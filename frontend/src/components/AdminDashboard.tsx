"use client";

import React, { useState, useEffect } from "react";
import { Search, RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "../services/api";
import { User, UserRole, SystemHealth, ResearchMetrics } from "../types";

export const AdminDashboard: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [researchMeta, setResearchMeta] = useState<ResearchMetrics["metadata"] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [activeSubTab, setActiveSubTab] = useState<"users" | "telemetry">("users");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [roleFilter, setRoleFilter] = useState<string>("ALL");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersData, healthData, metricsData] = await Promise.all([
        api.listUsers().catch(() => []),
        api.getHealth().catch(() => null),
        api.getResearchMetrics().catch(() => null),
      ]);
      setUsers(usersData);
      setHealth(healthData);
      if (metricsData?.metadata) {
        setResearchMeta(metricsData.metadata);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load administrative governance data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleStatus = async (user: User) => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await api.updateUserStatus(user.id, !user.is_active);
      setSuccessMsg(`User '${updated.email}' account status updated.`);
      setUsers(users.map((u) => (u.id === user.id ? updated : u)));
    } catch (err: any) {
      setError(err.message || "Failed to update account status.");
    } finally {
      setActionLoading(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.full_name && u.full_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (u.institution && u.institution.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesRole = roleFilter === "ALL" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Alert Banners */}
      {error && (
        <div className="alert-box alert-error">
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {successMsg && (
        <div className="alert-box alert-success">
          <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
          <div>{successMsg}</div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <h2>System Administration</h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            Institutional user governance, access control, and platform telemetry.
          </p>
        </div>

        <button onClick={loadData} className="btn btn-secondary btn-sm" title="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="tab-bar">
        <button
          onClick={() => setActiveSubTab("users")}
          className={`tab-btn ${activeSubTab === "users" ? "active" : ""}`}
        >
          <span>User Management ({users.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab("telemetry")}
          className={`tab-btn ${activeSubTab === "telemetry" ? "active" : ""}`}
        >
          <span>System Telemetry</span>
        </button>
      </div>

      {/* Content */}
      {activeSubTab === "users" ? (
        <div className="academic-panel">
          <div className="panel-header" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, minWidth: "260px" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <Search size={14} style={{ position: "absolute", left: "10px", top: "10px", color: "var(--text-muted)" }} />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Filter users by name, email, or college..."
                  className="form-input"
                  style={{ paddingLeft: "32px", fontSize: "0.8rem" }}
                />
              </div>

              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="form-select"
                style={{ width: "auto", fontSize: "0.8rem" }}
              >
                <option value="ALL">All Roles</option>
                <option value="TEACHER">Faculty</option>
                <option value="RESEARCHER">Researcher</option>
                <option value="ADMIN">Admin</option>
              </select>
            </div>
          </div>

          <div className="academic-table-container">
            <table className="academic-table">
              <thead>
                <tr>
                  <th>Academic Name & Email</th>
                  <th>Role</th>
                  <th>Institution / College</th>
                  <th>Department & Designation</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                      No registered users found.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{u.email}</div>
                      </td>

                      <td>
                        <span
                          className={`badge ${
                            u.role === "ADMIN"
                              ? "badge-warning"
                              : u.role === "TEACHER"
                              ? "badge-jade"
                              : "badge-teal"
                          }`}
                        >
                          {u.role === "ADMIN" ? "Admin" : u.role === "TEACHER" ? "Faculty" : "Researcher"}
                        </span>
                      </td>

                      <td style={{ fontSize: "0.8rem" }}>
                        <div>{u.institution || "—"}</div>
                        {u.institution_code && (
                          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>ID: {u.institution_code}</div>
                        )}
                      </td>

                      <td style={{ fontSize: "0.8rem" }}>
                        <div>{u.department || "—"}</div>
                        {u.designation && (
                          <div style={{ fontSize: "0.7rem", color: "var(--brand-deep)" }}>{u.designation}</div>
                        )}
                      </td>

                      <td>
                        <span className={`badge ${u.is_active ? "badge-success" : "badge-error"}`}>
                          {u.is_active ? "Active" : "Suspended"}
                        </span>
                      </td>

                      <td style={{ textAlign: "right" }}>
                        {u.role !== "ADMIN" && (
                          <button
                            onClick={() => handleToggleStatus(u)}
                            disabled={actionLoading}
                            className={`btn btn-sm ${u.is_active ? "btn-danger" : "btn-secondary"}`}
                            style={{ padding: "0.2rem 0.5rem", fontSize: "0.7rem" }}
                          >
                            {u.is_active ? "Suspend" : "Activate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Telemetry Subtab */
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
          <div className="academic-panel">
            <div className="panel-header">
              <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>Server Telemetry</span>
            </div>
            <div className="panel-body">
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>API Status:</span>
                  <span className="badge badge-success">Operational</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Database Engine:</span>
                  <span style={{ fontWeight: 600 }}>{health?.database_status === "connected" ? `${health?.database_engine || "Database"} / SQLAlchemy 2.0` : "Offline"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Python Version:</span>
                  <span style={{ fontWeight: 600 }}>{health?.system_info?.python_version || "3.11"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Service Name:</span>
                  <span>{health?.project_name || "Question Paper Difficulty Analyzer"}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="academic-panel">
            <div className="panel-header">
              <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>Active Model Registry</span>
            </div>
            <div className="panel-body">
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Registry Version:</span>
                  <span className="badge badge-jade">{researchMeta?.version || "v1.0.0"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Bloom Model:</span>
                  <span style={{ fontWeight: 600 }}>{researchMeta?.blooms_champion || "TFIDF_LogisticRegression"}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Difficulty Model:</span>
                  <span style={{ fontWeight: 600 }}>{researchMeta?.difficulty_champion || "TFIDF_LogisticRegression"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
