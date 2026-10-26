import {
  AuthResponse,
  Paper,
  PaperDetail,
  PaperAnalytics,
  User,
  UserRole,
  SystemHealth,
  ResearchMetrics,
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

class ApiService {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("cp_access_token");
  }

  public setToken(token: string | null) {
    if (typeof window === "undefined") return;
    if (token) {
      localStorage.setItem("cp_access_token", token);
    } else {
      localStorage.removeItem("cp_access_token");
    }
  }

  private getHeaders(isFormData = false): HeadersInit {
    const headers: Record<string, string> = {};
    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const isFormData = options.body instanceof FormData;
    const headers = {
      ...this.getHeaders(isFormData),
      ...(options.headers as Record<string, string>),
    };

    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === "string" 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fallback to text status
      }
      throw new Error(errorMessage);
    }

    // Handle empty or blob responses
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return (await res.json()) as T;
    }
    return (await res.text()) as unknown as T;
  }

  // -------------------------------------------------------------------------
  // Health
  // -------------------------------------------------------------------------
  async getHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>("/health", { cache: "no-store" });
  }

  // -------------------------------------------------------------------------
  // Auth
  // -------------------------------------------------------------------------
  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async register(payload: {
    email: string;
    full_name: string;
    password: string;
    role: UserRole;
    institution?: string;
    institution_code?: string;
    department?: string;
    designation?: string;
  }): Promise<User> {
    return this.request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>("/auth/me");
  }

  logout() {
    this.setToken(null);
  }

  // -------------------------------------------------------------------------
  // Examination Papers
  // -------------------------------------------------------------------------
  async listPapers(subject?: string, status?: string): Promise<Paper[]> {
    const params = new URLSearchParams();
    if (subject) params.append("subject", subject);
    if (status) params.append("status", status);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    return this.request<Paper[]>(`/papers${queryString}`);
  }

  async getPaper(id: number): Promise<PaperDetail> {
    return this.request<PaperDetail>(`/papers/${id}`);
  }

  async uploadPaper(formData: FormData): Promise<PaperDetail> {
    return this.request<PaperDetail>("/papers/upload", {
      method: "POST",
      body: formData,
    });
  }

  async analyzePaper(id: number): Promise<PaperDetail> {
    return this.request<PaperDetail>(`/papers/${id}/analyze`, {
      method: "POST",
    });
  }

  async getPaperAnalytics(id: number): Promise<PaperAnalytics> {
    return this.request<PaperAnalytics>(`/papers/${id}/analytics`);
  }

  async submitCorrection(
    paperId: number,
    questionId: number,
    payload: {
      corrected_blooms_level: string;
      corrected_difficulty: string;
      corrected_marks?: number | null;
      corrected_text?: string | null;
      rationale?: string | null;
    }
  ): Promise<any> {
    return this.request<any>(`/papers/${paperId}/questions/${questionId}/correction`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async deletePaper(id: number): Promise<{ message: string; id: number }> {
    return this.request<{ message: string; id: number }>(`/papers/${id}`, {
      method: "DELETE",
    });
  }

  async downloadReportPdf(paperId: number, filename = "Paper_Report.pdf") {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/papers/${paperId}/report/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed to download PDF report");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async downloadReportCsv(paperId: number, filename = "Paper_Dataset.csv") {
    const token = this.getToken();
    const res = await fetch(`${API_BASE_URL}/papers/${paperId}/report/csv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed to download CSV report");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // -------------------------------------------------------------------------
  // Admin User Governance
  // -------------------------------------------------------------------------
  async listUsers(): Promise<User[]> {
    return this.request<User[]>("/users/");
  }

  async updateUserStatus(userId: number, isActive: boolean): Promise<User> {
    return this.request<User>(`/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
  }

  async updateUserRole(userId: number, role: UserRole): Promise<User> {
    return this.request<User>(`/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  }

  // -------------------------------------------------------------------------
  // Researcher Endpoints
  // -------------------------------------------------------------------------
  async getResearchMetrics(): Promise<ResearchMetrics> {
    return this.request<ResearchMetrics>("/research/metrics");
  }

  async getAblations(): Promise<any> {
    return this.request<any>("/research/ablations");
  }

  async getDatasetStats(): Promise<any> {
    return this.request<any>("/research/dataset");
  }
}

export const api = new ApiService();
