"use client";

import React, { useState, useEffect } from "react";
import {
  Upload,
  FileText,
  Play,
  Download,
  Trash2,
  CheckCircle2,
  BarChart3,
  Layers,
  Edit3,
  X,
  FileSpreadsheet,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { api } from "../services/api";
import { Paper, PaperDetail, PaperAnalytics, Question } from "../types";

interface TeacherDashboardProps {
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export const TeacherDashboard: React.FC<TeacherDashboardProps> = ({ activeTab, onTabChange }) => {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedPaperId, setSelectedPaperId] = useState<number | null>(null);
  const [paperDetail, setPaperDetail] = useState<PaperDetail | null>(null);
  const [analytics, setAnalytics] = useState<PaperAnalytics | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Upload Form State
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [subject, setSubject] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [academicYear, setAcademicYear] = useState<string>("");
  const [term, setTerm] = useState<string>("");

  useEffect(() => {
    if (activeTab === "teacher_upload") {
      setShowUploadModal(true);
    }
  }, [activeTab]);

  const handleCloseUploadModal = () => {
    setShowUploadModal(false);
    if (onTabChange && activeTab === "teacher_upload") {
      onTabChange("teacher_papers");
    }
  };

  // Correction Modal State
  const [correctionTarget, setCorrectionTarget] = useState<Question | null>(null);
  const [correctedBloom, setCorrectedBloom] = useState<string>("Understand");
  const [correctedDiff, setCorrectedDiff] = useState<string>("Medium");
  const [correctedMarks, setCorrectedMarks] = useState<number | "">("");
  const [rationale, setRationale] = useState<string>("");

  const loadPapers = async () => {
    setLoading(true);
    try {
      const data = await api.listPapers();
      setPapers(data);
      if (data.length > 0 && !selectedPaperId) {
        setSelectedPaperId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load examination papers.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPapers();
  }, []);

  const loadPaperDetail = async (id: number) => {
    setActionLoading(true);
    setError(null);
    try {
      const detail = await api.getPaper(id);
      setPaperDetail(detail);

      if (detail.status === "ANALYZED" || detail.status === "REVIEWED") {
        try {
          const stats = await api.getPaperAnalytics(id);
          setAnalytics(stats);
        } catch {
          setAnalytics(null);
        }
      } else {
        setAnalytics(null);
      }
    } catch (err: any) {
      setError(err.message || "Could not retrieve examination details.");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    if (selectedPaperId) {
      loadPaperDetail(selectedPaperId);
    }
  }, [selectedPaperId]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setError("Please select a PDF or Word (.docx) examination document.");
      return;
    }

    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("title", title.trim() || uploadFile.name.replace(/\.[^/.]+$/, ""));
      formData.append("subject", subject.trim() || "General Examination");
      if (academicYear.trim()) formData.append("academic_year", academicYear.trim());
      if (term.trim()) formData.append("term", term.trim());

      const newPaper = await api.uploadPaper(formData);
      setSuccessMsg(`Document '${newPaper.title}' uploaded and parsed successfully.`);
      handleCloseUploadModal();
      setUploadFile(null);
      setTitle("");
      setSubject("");
      setAcademicYear("");
      setTerm("");
      await loadPapers();
      setSelectedPaperId(newPaper.id);
    } catch (err: any) {
      setError(err.message || "Failed to parse examination paper.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunAnalysis = async (paperId: number) => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await api.analyzePaper(paperId);
      setSuccessMsg("Dual-task classification completed.");
      await loadPaperDetail(paperId);
      await loadPapers();
    } catch (err: any) {
      setError(err.message || "Analysis execution failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenCorrection = (q: Question) => {
    const latestPred = q.predictions && q.predictions.length > 0 ? q.predictions[0] : null;
    const latestCorr = q.corrections && q.corrections.length > 0 ? q.corrections[0] : null;

    setCorrectionTarget(q);
    setCorrectedBloom(q.effective_blooms_level || latestCorr?.corrected_blooms_level || latestPred?.predicted_blooms_level || "Understand");
    setCorrectedDiff(q.effective_difficulty || latestCorr?.corrected_difficulty || latestPred?.predicted_difficulty || "Medium");
    setCorrectedMarks(q.marks !== null && q.marks !== undefined ? q.marks : "");
    setRationale(latestCorr?.rationale || "");
  };

  const handleSaveCorrection = async () => {
    if (!correctionTarget || !selectedPaperId) return;

    setActionLoading(true);
    setError(null);
    try {
      await api.submitCorrection(selectedPaperId, correctionTarget.id, {
        corrected_blooms_level: correctedBloom,
        corrected_difficulty: correctedDiff,
        corrected_marks: correctedMarks === "" ? null : Number(correctedMarks),
        rationale: rationale.trim() || "Instructional calibration verified by faculty.",
      });

      setSuccessMsg(`Question ${correctionTarget.question_number} calibration saved.`);
      setCorrectionTarget(null);
      await loadPaperDetail(selectedPaperId);
    } catch (err: any) {
      setError(err.message || "Failed to save question calibration.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeletePaper = async (paperId: number) => {
    if (!window.confirm("Permanently delete this examination paper?")) {
      return;
    }

    setActionLoading(true);
    setError(null);
    try {
      await api.deletePaper(paperId);
      setSuccessMsg("Document deleted.");
      setSelectedPaperId(null);
      setPaperDetail(null);
      await loadPapers();
    } catch (err: any) {
      setError(err.message || "Failed to remove document.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadPdf = async (paperId: number, paperTitle: string) => {
    try {
      await api.downloadReportPdf(paperId, `${paperTitle.toLowerCase().replace(/\s+/g, "_")}_report.pdf`);
    } catch (err: any) {
      setError(err.message || "Failed to export PDF report.");
    }
  };

  const handleDownloadCsv = async (paperId: number, paperTitle: string) => {
    try {
      await api.downloadReportCsv(paperId, `${paperTitle.toLowerCase().replace(/\s+/g, "_")}_questions.csv`);
    } catch (err: any) {
      setError(err.message || "Failed to export CSV report.");
    }
  };

  const getBloomBadgeClass = (bloom: string) => {
    switch (bloom?.toUpperCase()) {
      case "REMEMBER": return "badge-bloom-remember";
      case "UNDERSTAND": return "badge-bloom-understand";
      case "APPLY": return "badge-bloom-apply";
      case "ANALYZE": return "badge-bloom-analyze";
      case "EVALUATE": return "badge-bloom-evaluate";
      case "CREATE": return "badge-bloom-create";
      default: return "badge-jade";
    }
  };

  const getDiffBadgeClass = (diff: string) => {
    switch (diff?.toUpperCase()) {
      case "EASY": return "badge-diff-easy";
      case "MEDIUM": return "badge-diff-medium";
      case "HARD": return "badge-diff-hard";
      default: return "badge-warning";
    }
  };

  const BLOOM_COLORS: Record<string, string> = {
    Remember: "#087F83",
    Understand: "#167C68",
    Apply: "#2B7A78",
    Analyze: "#3479B7",
    Evaluate: "#B97818",
    Create: "#F28C45",
  };

  const DIFF_COLORS: Record<string, string> = {
    Easy: "#218653",
    Medium: "#B97818",
    Hard: "#C43D48",
  };

  const bloomChartData = analytics?.blooms_distribution
    ? Object.entries(analytics.blooms_distribution).map(([name, item]) => ({
        name,
        count: item.count,
        fill: BLOOM_COLORS[name] || "#167C68",
      }))
    : [];

  const diffChartData = analytics?.difficulty_distribution
    ? Object.entries(analytics.difficulty_distribution).map(([name, item]) => ({
        name,
        count: item.count,
        fill: DIFF_COLORS[name] || "#B97818",
      }))
    : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Alerts */}
      {error && (
        <div className="alert-box alert-error">
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>{error}</div>
          <button onClick={() => setError(null)} style={{ background: "none", border: "none", cursor: "pointer" }}>
            <X size={14} />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="alert-box alert-success">
          <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>{successMsg}</div>
          <button onClick={() => setSuccessMsg(null)} style={{ background: "none", border: "none", cursor: "pointer" }}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Action Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <h2>Examination Papers</h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            Upload and review question papers across Bloom’s Taxonomy and Difficulty.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={loadPapers} className="btn btn-secondary btn-sm" title="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
          <button onClick={() => setShowUploadModal(true)} className="btn btn-primary btn-sm">
            <Upload size={14} />
            <span>Upload Paper</span>
          </button>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "1.25rem", alignItems: "start" }}>
        {/* Left Column: Papers List */}
        <div className="academic-panel">
          <div className="panel-header">
            <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>
              My Papers ({papers.length})
            </span>
          </div>

          <div style={{ padding: "0.5rem", maxHeight: "600px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {papers.length === 0 ? (
              <div style={{ padding: "2rem 1rem", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                No examination papers uploaded yet.
              </div>
            ) : (
              papers.map((p) => {
                const isSelected = selectedPaperId === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPaperId(p.id)}
                    style={{
                      padding: "0.75rem",
                      borderRadius: "var(--radius-sm)",
                      border: isSelected ? "1.5px solid var(--brand-primary)" : "1px solid var(--border-light)",
                      backgroundColor: isSelected ? "var(--bg-sage-light)" : "var(--bg-surface)",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.4rem" }}>
                      <div style={{ fontWeight: 600, fontSize: "0.825rem", color: isSelected ? "var(--brand-deep)" : "var(--text-main)" }}>
                        {p.title}
                      </div>
                      <span className="badge badge-jade" style={{ fontSize: "0.65rem" }}>
                        {p.file_type?.toUpperCase()}
                      </span>
                    </div>

                    <div style={{ fontSize: "0.725rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
                      {p.subject} {p.term ? `• ${p.term}` : ""}
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.4rem", fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      <span>{p.total_questions || 0} questions</span>
                      <span className={`badge ${p.status === "ANALYZED" || p.status === "REVIEWED" ? "badge-success" : "badge-warning"}`} style={{ fontSize: "0.625rem" }}>
                        {p.status}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Selected Paper Details */}
        <div>
          {paperDetail ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <div className="academic-panel">
                {/* Header and Actions */}
                <div className="panel-header" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
                  <div>
                    <h3 style={{ fontSize: "1rem" }}>{paperDetail.title}</h3>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.15rem" }}>
                      {paperDetail.subject} • {paperDetail.file_type?.toUpperCase()} • {paperDetail.total_marks ? `${paperDetail.total_marks} Marks` : "Marks not assigned"}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                    {paperDetail.status === "UPLOADED" || paperDetail.status === "EXTRACTED" ? (
                      <button
                        onClick={() => handleRunAnalysis(paperDetail.id)}
                        disabled={actionLoading}
                        className="btn btn-primary btn-sm"
                      >
                        <Play size={14} />
                        <span>Run Analysis</span>
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => handleDownloadPdf(paperDetail.id, paperDetail.title)}
                          className="btn btn-secondary btn-sm"
                        >
                          <Download size={13} />
                          <span>PDF Report</span>
                        </button>

                        <button
                          onClick={() => handleDownloadCsv(paperDetail.id, paperDetail.title)}
                          className="btn btn-secondary btn-sm"
                        >
                          <FileSpreadsheet size={13} />
                          <span>CSV Export</span>
                        </button>
                      </>
                    )}

                    <button
                      onClick={() => handleDeletePaper(paperDetail.id)}
                      className="btn btn-danger btn-icon"
                      title="Delete paper"
                      style={{ width: "28px", height: "28px" }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {/* Charts (Only displayed when analysis is complete) */}
                {analytics && (
                  <div style={{ padding: "1rem", borderBottom: "1px solid var(--border-light)", backgroundColor: "#FAF9F5" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                      <div className="academic-card" style={{ padding: "0.75rem" }}>
                        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "0.4rem" }}>
                          Bloom’s Taxonomy Distribution
                        </div>
                        <div style={{ width: "100%", height: 140 }}>
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={bloomChartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                              <XAxis dataKey="name" tick={{ fontSize: 9 }} interval={0} />
                              <YAxis tick={{ fontSize: 9 }} allowDecimals={false} />
                              <Tooltip />
                              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                                {bloomChartData.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="academic-card" style={{ padding: "0.75rem" }}>
                        <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "0.4rem" }}>
                          Question Difficulty Distribution
                        </div>
                        <div style={{ width: "100%", height: 140 }}>
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={diffChartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                              <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                              <YAxis tick={{ fontSize: 9 }} allowDecimals={false} />
                              <Tooltip />
                              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                                {diffChartData.map((entry, index) => (
                                  <Cell key={`diff-${index}`} fill={entry.fill} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Questions Table */}
                <div style={{ padding: "1rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>
                      Questions ({paperDetail.questions?.length || 0})
                    </span>
                  </div>

                  <div className="academic-table-container">
                    <table className="academic-table">
                      <thead>
                        <tr>
                          <th style={{ width: "50px" }}>Q #</th>
                          <th>Prompt Text</th>
                          <th style={{ width: "110px" }}>Bloom Level</th>
                          <th style={{ width: "100px" }}>Difficulty</th>
                          <th style={{ width: "70px" }}>Marks</th>
                          <th style={{ width: "80px", textAlign: "right" }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(paperDetail.questions || []).map((q) => {
                          const latestPred = q.predictions && q.predictions.length > 0 ? q.predictions[0] : null;
                          const latestCorr = q.corrections && q.corrections.length > 0 ? q.corrections[0] : null;
                          const effectiveBloom = q.effective_blooms_level || latestCorr?.corrected_blooms_level || latestPred?.predicted_blooms_level || "Pending";
                          const effectiveDiff = q.effective_difficulty || latestCorr?.corrected_difficulty || latestPred?.predicted_difficulty || "Pending";

                          return (
                            <tr key={q.id}>
                              <td style={{ fontWeight: 600 }}>{q.question_number}</td>
                              <td style={{ fontSize: "0.8rem", maxWidth: "360px" }}>
                                <div>{q.question_text}</div>
                                {latestCorr?.rationale && (
                                  <div style={{ fontSize: "0.7rem", color: "var(--brand-deep)", marginTop: "2px" }}>
                                    Justification: {latestCorr.rationale}
                                  </div>
                                )}
                              </td>
                              <td>
                                <span className={`badge ${getBloomBadgeClass(effectiveBloom)}`}>
                                  {effectiveBloom}
                                </span>
                              </td>
                              <td>
                                <span className={`badge ${getDiffBadgeClass(effectiveDiff)}`}>
                                  {effectiveDiff}
                                </span>
                              </td>
                              <td style={{ fontWeight: 600, fontSize: "0.775rem" }}>
                                {q.marks !== null && q.marks !== undefined ? `${q.marks} pts` : "—"}
                              </td>
                              <td style={{ textAlign: "right" }}>
                                <button
                                  onClick={() => handleOpenCorrection(q)}
                                  className="btn btn-secondary btn-sm"
                                  style={{ padding: "0.2rem 0.45rem", fontSize: "0.7rem" }}
                                >
                                  <Edit3 size={11} />
                                  <span>Review</span>
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="academic-panel" style={{ padding: "2.5rem 1rem", textAlign: "center", color: "var(--text-secondary)" }}>
              <p style={{ fontSize: "0.85rem" }}>Select an examination paper from the left panel to review questions.</p>
            </div>
          )}
        </div>
      </div>

      {/* Upload Paper Modal */}
      {showUploadModal && (
        <div className="modal-backdrop" onClick={handleCloseUploadModal}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h3 className="modal-title">Upload Examination Paper</h3>
              <button onClick={handleCloseUploadModal} className="btn btn-secondary btn-icon" style={{ width: "26px", height: "26px" }}>
                <X size={14} />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                    <label className="form-label" style={{ marginBottom: 0 }}>Select Document (PDF or DOCX) *</label>
                    <span style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>Up to 1 GB</span>
                  </div>
                  <input
                    type="file"
                    required
                    accept=".pdf,.docx"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                        if (!title) {
                          setTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ""));
                        }
                      }
                    }}
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Paper Title *</label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Midterm Examination"
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Course / Subject *</label>
                  <input
                    type="text"
                    required
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="e.g. Computer Science"
                    className="form-input"
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                  <div className="form-group">
                    <label className="form-label">Academic Year</label>
                    <input
                      type="text"
                      value={academicYear}
                      onChange={(e) => setAcademicYear(e.target.value)}
                      placeholder="e.g. 2026"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Term / Semester</label>
                    <input
                      type="text"
                      value={term}
                      onChange={(e) => setTerm(e.target.value)}
                      placeholder="e.g. Spring"
                      className="form-input"
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={handleCloseUploadModal} className="btn btn-secondary btn-sm">
                  Cancel
                </button>
                <button type="submit" disabled={actionLoading || !uploadFile} className="btn btn-primary btn-sm">
                  {actionLoading ? "Uploading..." : "Upload Paper"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {correctionTarget && (
        <div className="modal-backdrop" onClick={() => setCorrectionTarget(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h3 className="modal-title">Review Question #{correctionTarget.question_number}</h3>
              <button onClick={() => setCorrectionTarget(null)} className="btn btn-secondary btn-icon" style={{ width: "26px", height: "26px" }}>
                <X size={14} />
              </button>
            </div>

            <div className="modal-body">
              <div style={{ fontSize: "0.8rem", color: "var(--text-main)", marginBottom: "1rem", padding: "0.75rem", backgroundColor: "#FAF9F5", borderRadius: "4px" }}>
                {correctionTarget.question_text}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                <div className="form-group">
                  <label className="form-label">Bloom's Taxonomy Level</label>
                  <select
                    value={correctedBloom}
                    onChange={(e) => setCorrectedBloom(e.target.value)}
                    className="form-select"
                  >
                    <option value="Remember">Remember</option>
                    <option value="Understand">Understand</option>
                    <option value="Apply">Apply</option>
                    <option value="Analyze">Analyze</option>
                    <option value="Evaluate">Evaluate</option>
                    <option value="Create">Create</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Difficulty Tier</label>
                  <select
                    value={correctedDiff}
                    onChange={(e) => setCorrectedDiff(e.target.value)}
                    className="form-select"
                  >
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Marks</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={correctedMarks}
                  onChange={(e) => setCorrectedMarks(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="Optional marks"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Instructional Justification</label>
                <textarea
                  rows={2}
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  placeholder="Reason for classification adjustment..."
                  className="form-textarea"
                />
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" onClick={() => setCorrectionTarget(null)} className="btn btn-secondary btn-sm">
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveCorrection}
                disabled={actionLoading}
                className="btn btn-primary btn-sm"
              >
                {actionLoading ? "Saving..." : "Save Calibration"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
