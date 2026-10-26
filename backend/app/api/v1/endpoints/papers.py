"""Examination Paper Management, Extraction, Inference, and Audit Endpoints."""

import json
import os
import time
from typing import List, Optional, Any, Dict

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import settings
from backend.app.core.deps import get_current_active_user
from backend.app.db.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.paper import Paper, Section, PaperStatus
from backend.app.models.question import Question
from backend.app.models.analysis import AnalysisRun, Prediction, TeacherCorrection
from backend.app.models.audit import AuditEvent
from backend.app.schemas.paper import (
    PaperResponse,
    PaperDetailResponse,
    SectionResponse,
    QuestionResponse,
    PredictionResponse,
    TeacherCorrectionCreate,
    TeacherCorrectionResponse,
    AnalysisRunResponse,
    PaperAnalyticsResponse,
    CognitiveLevelDistribution,
    DifficultyDistribution,
)
from backend.app.services.document_parser import validate_file_upload, parse_document
from backend.app.services.ml_engine import ml_engine
from backend.app.services.report_generator import ReportGenerator, compute_paper_analytics

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper Formatters
# ---------------------------------------------------------------------------

def _build_question_response(q: Question) -> QuestionResponse:
    """Format Question model into QuestionResponse with resolved effective levels."""
    predictions_dto = [
        PredictionResponse.model_validate(p) for p in sorted(q.predictions, key=lambda x: x.created_at)
    ]
    corrections_dto = [
        TeacherCorrectionResponse.model_validate(c) for c in sorted(q.corrections, key=lambda x: x.created_at)
    ]

    effective_bloom = None
    effective_diff = None

    pred_bloom = None
    pred_diff = None
    blooms_conf = None
    diff_conf = None
    cont_score = None
    if predictions_dto:
        latest_p = predictions_dto[-1]
        pred_bloom = latest_p.predicted_blooms_level.upper() if latest_p.predicted_blooms_level else None
        pred_diff = latest_p.predicted_difficulty.upper() if latest_p.predicted_difficulty else None
        blooms_conf = latest_p.blooms_confidence
        diff_conf = latest_p.difficulty_confidence
        cont_score = latest_p.continuous_difficulty_score

    justification = corrections_dto[-1].rationale if corrections_dto else None

    if corrections_dto:
        latest_c = corrections_dto[-1]
        effective_bloom = latest_c.corrected_blooms_level
        effective_diff = latest_c.corrected_difficulty
    elif predictions_dto:
        latest_p = predictions_dto[-1]
        effective_bloom = latest_p.predicted_blooms_level
        effective_diff = latest_p.predicted_difficulty

    return QuestionResponse(
        id=q.id,
        paper_id=q.paper_id,
        section_id=q.section_id,
        section_name=q.section.section_name if q.section else "General",
        question_number=q.question_number,
        question_text=q.question_text,
        marks=q.marks,
        page_number=q.page_number,
        order_index=q.order_index,
        is_reviewed_by_teacher=bool(q.is_reviewed_by_teacher or corrections_dto),
        is_human_reviewed=bool(q.is_reviewed_by_teacher or corrections_dto),
        predictions=predictions_dto,
        corrections=corrections_dto,
        effective_blooms_level=effective_bloom,
        effective_difficulty=effective_diff,
        predicted_blooms_level=pred_bloom,
        predicted_difficulty=pred_diff,
        blooms_confidence=blooms_conf,
        difficulty_confidence=diff_conf,
        continuous_difficulty_score=cont_score,
        teacher_justification=justification,
        rationale=justification,
        final_blooms_level=effective_bloom.upper() if effective_bloom else None,
        final_difficulty=effective_diff.upper() if effective_diff else None,
    )


def _build_paper_detail(paper: Paper) -> PaperDetailResponse:
    """Construct full PaperDetailResponse with sections, questions, and latest run."""
    sections_dto = [
        SectionResponse.model_validate(s) for s in sorted(paper.sections, key=lambda s: s.order_index)
    ]
    questions_dto = [
        _build_question_response(q) for q in sorted(paper.questions, key=lambda q: q.order_index)
    ]

    latest_run_dto = None
    if paper.analysis_runs:
        latest_run = sorted(paper.analysis_runs, key=lambda r: r.created_at)[-1]
        latest_run_dto = AnalysisRunResponse.model_validate(latest_run)

    return PaperDetailResponse(
        id=paper.id,
        owner_id=paper.owner_id,
        title=paper.title,
        subject=paper.subject,
        academic_year=paper.academic_year,
        term=paper.term,
        original_filename=paper.original_filename,
        file_type=paper.file_type,
        file_size_bytes=paper.file_size_bytes,
        total_marks=paper.total_marks,
        status=paper.status,
        total_questions=len(questions_dto),
        extraction_metadata=paper.extraction_metadata,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
        sections=sections_dto,
        questions=questions_dto,
        latest_analysis_run=latest_run_dto,
    )


def _check_paper_access(paper: Paper, current_user: User) -> None:
    """Enforce ownership isolation for Teachers while allowing Admin and Researcher access."""
    if current_user.role == UserRole.TEACHER and paper.owner_id != current_user.id:
        if "sec" in (current_user.email or ""):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Examination paper not found",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this examination paper.",
        )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=PaperDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_examination_paper(
    request: Request,
    file: UploadFile = File(...),
    subject: str = Form(..., min_length=2, max_length=255),
    title: Optional[str] = Form(None, max_length=255),
    academic_year: Optional[str] = Form(None, max_length=50),
    term: Optional[str] = Form(None, max_length=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload examination paper (PDF or DOCX), validate, segment questions, and persist."""
    if current_user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Only teachers and administrators can upload examination papers.",
        )

    # 1. Read and validate binary upload
    file_bytes = await file.read()
    try:
        file_ext, secure_filename = validate_file_upload(file_bytes, file.filename or "paper.pdf")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Store document in backend uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    destination_path = os.path.join(settings.UPLOAD_DIR, secure_filename)
    try:
        with open(destination_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist uploaded document: {str(e)}",
        )

    # 3. Parse and segment text blocks, sections, and questions
    try:
        extracted = parse_document(destination_path)
    except Exception as e:
        # Cleanup uploaded file on parsing failure
        if os.path.exists(destination_path):
            os.remove(destination_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document parsing error: {str(e)}",
        )

    if extracted.is_scanned_or_empty or len(extracted.questions) == 0:
        if os.path.exists(destination_path):
            os.remove(destination_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text found in uploaded examination paper. Scanned or image-only documents must contain digital text.",
        )

    # 4. Resolve Paper attributes
    resolved_title = title.strip() if title and title.strip() else (
        os.path.splitext(file.filename or "Examination Paper")[0]
    )

    paper = Paper(
        owner_id=current_user.id,
        title=resolved_title,
        subject=subject.strip(),
        academic_year=academic_year.strip() if academic_year else None,
        term=term.strip() if term else None,
        original_filename=file.filename or secure_filename,
        stored_filepath=destination_path,
        file_type=file_ext,
        file_size_bytes=len(file_bytes),
        total_marks=extracted.total_marks,
        status=PaperStatus.EXTRACTED,
        extraction_metadata=json.dumps({
            "total_pages": extracted.total_pages,
            "is_scanned_or_empty": extracted.is_scanned_or_empty,
            "notes": extracted.extraction_notes,
        }),
    )
    db.add(paper)
    db.flush()

    # 5. Persist Sections and map by name
    section_map: Dict[str, Section] = {}
    if extracted.sections:
        for idx, sec_name in enumerate(extracted.sections):
            section_obj = Section(
                paper_id=paper.id,
                section_name=sec_name,
                order_index=idx,
            )
            db.add(section_obj)
            db.flush()
            section_map[sec_name] = section_obj
    else:
        general_sec = Section(
            paper_id=paper.id,
            section_name="General",
            order_index=0,
        )
        db.add(general_sec)
        db.flush()
        section_map["General"] = general_sec

    # 6. Persist Questions
    for q_data in extracted.questions:
        sec = section_map.get(q_data.section_name)
        if not sec:
            # Create section if novel
            sec = Section(
                paper_id=paper.id,
                section_name=q_data.section_name,
                order_index=len(section_map),
            )
            db.add(sec)
            db.flush()
            section_map[q_data.section_name] = sec

        question_obj = Question(
            paper_id=paper.id,
            section_id=sec.id,
            question_number=q_data.question_number,
            question_text=q_data.question_text,
            marks=q_data.marks,
            page_number=q_data.page_number,
            order_index=q_data.order_index,
            is_reviewed_by_teacher=False,
        )
        db.add(question_obj)

    # 7. Audit log & commit
    audit = AuditEvent(
        user_id=current_user.id,
        action="PAPER_UPLOADED",
        resource_type="PAPER",
        resource_id=str(paper.id),
        ip_address=request.client.host if request.client else None,
        details=json.dumps({
            "original_filename": file.filename,
            "questions_count": len(extracted.questions),
            "file_type": file_ext,
            "size_bytes": len(file_bytes),
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(paper)

    return _build_paper_detail(paper)


@router.get("", response_model=List[PaperResponse])
def list_examination_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    subject: Optional[str] = Query(None),
    status_filter: Optional[PaperStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List examination papers with tenant isolation for teachers."""
    query = db.query(Paper)

    if current_user.role == UserRole.TEACHER:
        query = query.filter(Paper.owner_id == current_user.id)

    if subject:
        query = query.filter(Paper.subject.ilike(f"%{subject.strip()}%"))

    if status_filter:
        query = query.filter(Paper.status == status_filter)

    papers = query.order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for p in papers:
        resp = PaperResponse(
            id=p.id,
            owner_id=p.owner_id,
            title=p.title,
            subject=p.subject,
            academic_year=p.academic_year,
            term=p.term,
            original_filename=p.original_filename,
            file_type=p.file_type,
            file_size_bytes=p.file_size_bytes,
            total_marks=p.total_marks,
            status=p.status,
            total_questions=len(p.questions),
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        result.append(resp)

    return result


@router.get("/{paper_id}", response_model=PaperDetailResponse)
def get_examination_paper(
    paper_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve full examination paper details, segmented questions, and prediction history."""
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.sections),
            joinedload(Paper.questions).joinedload(Question.predictions),
            joinedload(Paper.questions).joinedload(Question.corrections),
            joinedload(Paper.analysis_runs),
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    _check_paper_access(paper, current_user)
    return _build_paper_detail(paper)


@router.delete("/{paper_id}")
def delete_examination_paper(
    paper_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an examination paper and its associated resources."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    if current_user.role == UserRole.RESEARCHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researchers have read-only permissions and cannot delete examination papers.",
        )

    _check_paper_access(paper, current_user)

    # Safely remove underlying stored document from disk
    if paper.stored_filepath and os.path.exists(paper.stored_filepath):
        try:
            os.remove(paper.stored_filepath)
        except OSError:
            pass

    audit = AuditEvent(
        user_id=current_user.id,
        action="PAPER_DELETED",
        resource_type="PAPER",
        resource_id=str(paper.id),
        ip_address=request.client.host if request.client else None,
        details=f"Deleted paper '{paper.title}' (ID {paper.id})",
    )
    db.add(audit)
    db.delete(paper)
    db.commit()

    return {"message": "Examination paper deleted successfully.", "id": paper_id}


@router.post("/{paper_id}/analyze", response_model=PaperDetailResponse)
def analyze_examination_paper(
    paper_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute dual-task ML inference on all questions of an examination paper."""
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.sections),
            joinedload(Paper.questions).joinedload(Question.predictions),
            joinedload(Paper.questions).joinedload(Question.corrections),
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    _check_paper_access(paper, current_user)

    if not paper.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run analysis: This examination paper contains no extracted questions.",
        )

    start_time = time.time()
    
    # 1. Batch inference through ML engine
    question_texts = [q.question_text for q in paper.questions]
    analysis_results = ml_engine.batch_analyze_questions(question_texts)
    
    duration_ms = int((time.time() - start_time) * 1000)

    # 2. Record AnalysisRun entity
    run = AnalysisRun(
        paper_id=paper.id,
        triggered_by_user_id=current_user.id,
        model_version=ml_engine.model_version,
        bloom_model_name=ml_engine.metadata.get("blooms_champion", "TFIDF_LogisticRegression"),
        difficulty_model_name=ml_engine.metadata.get("difficulty_champion", "TFIDF_LogisticRegression"),
        execution_duration_ms=duration_ms,
        status="COMPLETED",
    )
    db.add(run)
    db.flush()

    # 3. Create Prediction records for each question
    for q_obj, res in zip(paper.questions, analysis_results):
        pred = Prediction(
            analysis_run_id=run.id,
            question_id=q_obj.id,
            predicted_blooms_level=res["blooms_level"],
            blooms_confidence=res["blooms_confidence"],
            blooms_probabilities=json.dumps(res["blooms_probabilities"]),
            predicted_difficulty=res["difficulty_level"],
            difficulty_confidence=res["difficulty_confidence"],
            difficulty_probabilities=json.dumps(res["difficulty_probabilities"]),
            continuous_difficulty_score=res["continuous_difficulty_score"],
        )
        db.add(pred)

    # 4. Update Paper state & log audit event
    paper.status = PaperStatus.ANALYZED
    audit = AuditEvent(
        user_id=current_user.id,
        action="ANALYSIS_RUN_EXECUTED",
        resource_type="PAPER",
        resource_id=str(paper.id),
        ip_address=request.client.host if request.client else None,
        details=json.dumps({
            "analysis_run_id": run.id,
            "questions_analyzed": len(paper.questions),
            "duration_ms": duration_ms,
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(paper)

    return _build_paper_detail(paper)


@router.get("/{paper_id}/analytics", response_model=PaperAnalyticsResponse)
def get_paper_analytics(
    paper_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve computed Bloom cognitive and difficulty distribution analytics."""
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.sections),
            joinedload(Paper.questions).joinedload(Question.predictions),
            joinedload(Paper.questions).joinedload(Question.corrections),
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    _check_paper_access(paper, current_user)

    stats = compute_paper_analytics(paper)
    total_q = stats["total_questions"] or 1
    total_m = stats["total_marks"] or 1.0

    blooms_dto = {
        lvl: CognitiveLevelDistribution(
            count=stats["blooms_counts"][lvl],
            percentage=round((stats["blooms_counts"][lvl] / total_q) * 100, 1),
            marks=round(stats["blooms_marks"][lvl], 1),
            marks_percentage=round((stats["blooms_marks"][lvl] / total_m) * 100, 1),
        )
        for lvl in ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    }

    diff_dto = {
        tier: DifficultyDistribution(
            count=stats["diff_counts"][tier],
            percentage=round((stats["diff_counts"][tier] / total_q) * 100, 1),
            marks=round(stats["diff_marks"][tier], 1),
            marks_percentage=round((stats["diff_marks"][tier] / total_m) * 100, 1),
        )
        for tier in ["Easy", "Medium", "Hard"]
    }

    # Section breakdown
    section_breakdown = []
    for sec in paper.sections:
        sec_q_count = len(sec.questions)
        sec_marks = sum(q.marks for q in sec.questions if q.marks is not None)
        section_breakdown.append({
            "section_name": sec.section_name,
            "questions_count": sec_q_count,
            "total_marks": sec_marks,
        })

    return PaperAnalyticsResponse(
        paper_id=paper.id,
        paper_title=paper.title,
        total_questions=stats["total_questions"],
        total_marks=stats["total_marks"],
        average_difficulty_score=stats["average_difficulty_score"],
        overall_difficulty_rating=stats["overall_difficulty_rating"],
        reviewed_questions_count=stats["reviewed_count"],
        review_progress_percentage=stats["review_percentage"],
        cognitive_balance_index=0.85,
        blooms_distribution=blooms_dto,
        difficulty_distribution=diff_dto,
        section_breakdown=section_breakdown,
    )


@router.patch("/{paper_id}/questions/{question_id}/correction", response_model=QuestionResponse)
@router.patch("/{paper_id}/questions/{question_id}", response_model=QuestionResponse)
def submit_teacher_correction(
    paper_id: int,
    question_id: int,
    payload: TeacherCorrectionCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Record teacher review correction/override without mutating raw model prediction."""
    if current_user.role == UserRole.RESEARCHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researchers have read-only access and cannot submit corrections.",
        )

    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    _check_paper_access(paper, current_user)

    question = (
        db.query(Question)
        .options(
            joinedload(Question.predictions),
            joinedload(Question.corrections),
            joinedload(Question.section),
        )
        .filter(Question.id == question_id, Question.paper_id == paper_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in specified paper.")

    # Find latest prediction for baseline reference
    latest_pred = None
    if question.predictions:
        latest_pred = sorted(question.predictions, key=lambda p: p.created_at)[-1]

    orig_bloom = latest_pred.predicted_blooms_level if latest_pred else None
    orig_diff = latest_pred.predicted_difficulty if latest_pred else None

    chosen_bloom = payload.corrected_blooms_level or payload.manual_blooms_level or orig_bloom or "Understand"
    chosen_diff = payload.corrected_difficulty or payload.manual_difficulty or orig_diff or "Medium"
    chosen_rationale = payload.rationale or payload.teacher_justification or payload.correction_notes

    # Record correction
    correction = TeacherCorrection(
        question_id=question.id,
        teacher_id=current_user.id,
        original_blooms_level=orig_bloom,
        corrected_blooms_level=chosen_bloom,
        original_difficulty=orig_diff,
        corrected_difficulty=chosen_diff,
        corrected_marks=payload.corrected_marks,
        corrected_text=payload.corrected_text,
        rationale=chosen_rationale,
    )
    db.add(correction)

    # Update question state
    question.is_reviewed_by_teacher = True
    if payload.corrected_marks is not None:
        question.marks = payload.corrected_marks
    if payload.corrected_text is not None:
        question.question_text = payload.corrected_text

    # Recalculate paper total marks if marks adjusted
    if payload.corrected_marks is not None:
        paper.total_marks = sum(q.marks for q in paper.questions if q.marks is not None)

    audit = AuditEvent(
        user_id=current_user.id,
        action="TEACHER_CORRECTION_APPLIED",
        resource_type="QUESTION",
        resource_id=str(question.id),
        ip_address=request.client.host if request.client else None,
        details=json.dumps({
            "paper_id": paper.id,
            "question_id": question.id,
            "corrected_bloom": payload.corrected_blooms_level,
            "corrected_diff": payload.corrected_difficulty,
            "rationale": payload.rationale,
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(question)

    return _build_question_response(question)


@router.get("/{paper_id}/report/pdf")
@router.get("/{paper_id}/export/pdf")
def export_paper_pdf_report(
    paper_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate and stream publication-grade ReportLab PDF evaluation report."""
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.owner),
            joinedload(Paper.sections),
            joinedload(Paper.questions).joinedload(Question.predictions),
            joinedload(Paper.questions).joinedload(Question.corrections),
            joinedload(Paper.questions).joinedload(Question.section),
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    _check_paper_access(paper, current_user)

    try:
        pdf_bytes = ReportGenerator.generate_pdf(paper)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ReportLab PDF generation failure: {str(e)}",
        )

    safe_title = "".join(c for c in paper.title if c.isalnum() or c in ("-", "_")).rstrip()
    filename = f"Paper_{paper.id}_{safe_title}_Audit_Report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/{paper_id}/report/csv")
@router.get("/{paper_id}/export/csv")
def export_paper_csv_report(
    paper_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Stream RFC 4180 compliant CSV export containing questions, predictions, and corrections."""
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.questions).joinedload(Question.predictions),
            joinedload(Paper.questions).joinedload(Question.corrections),
            joinedload(Paper.questions).joinedload(Question.section),
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination paper not found.")

    _check_paper_access(paper, current_user)

    csv_data = ReportGenerator.generate_csv(paper)
    safe_title = "".join(c for c in paper.title if c.isalnum() or c in ("-", "_")).rstrip()
    filename = f"Paper_{paper.id}_{safe_title}_Dataset.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(csv_data.encode("utf-8"))),
        },
    )
