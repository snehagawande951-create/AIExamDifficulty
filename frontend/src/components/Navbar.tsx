"use client";

import React from "react";
import { LogOut } from "lucide-react";
import { User } from "../types";

interface NavbarProps {
  currentUser: User | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenAuth: (mode?: "login" | "register") => void;
  onLogout: () => void;
  backendOnline: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  activeTab,
  setActiveTab,
  onOpenAuth,
  onLogout,
  backendOnline,
}) => {
  const getRoleLabel = (role: string) => {
    switch (role) {
      case "ADMIN":
        return "Administrator";
      case "TEACHER":
        return "Faculty";
      case "RESEARCHER":
        return "Researcher";
      default:
        return role;
    }
  };

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        {/* Brand */}
        <div
          className="navbar-brand"
          onClick={() => {
            if (currentUser) {
              if (currentUser.role === "TEACHER") setActiveTab("teacher_papers");
              else if (currentUser.role === "ADMIN") setActiveTab("admin_users");
              else if (currentUser.role === "RESEARCHER") setActiveTab("research_benchmarks");
            } else {
              setActiveTab("landing");
            }
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="brand-title">
                AI Exam Analyzer
              </span>
              <span className="badge badge-jade" style={{ fontSize: "0.65rem", padding: "0.15rem 0.4rem" }}>
                Academic Platform
              </span>
            </div>
            <p className="brand-subtitle">
              Automated Examination Demand & Bloom’s Taxonomy
            </p>
          </div>
        </div>

        {/* Navigation Tabs for Active User */}
        <nav className="navbar-nav">
          {currentUser?.role === "TEACHER" && (
            <>
              <button
                onClick={() => setActiveTab("teacher_papers")}
                className={`nav-tab ${activeTab === "teacher_papers" ? "active" : ""}`}
              >
                <span>Examination Papers</span>
              </button>
              <button
                onClick={() => setActiveTab("teacher_upload")}
                className={`nav-tab ${activeTab === "teacher_upload" ? "active" : ""}`}
              >
                <span>Upload Paper</span>
              </button>
            </>
          )}

          {currentUser?.role === "ADMIN" && (
            <>
              <button
                onClick={() => setActiveTab("admin_users")}
                className={`nav-tab ${activeTab === "admin_users" ? "active" : ""}`}
              >
                <span>User Management</span>
              </button>
              <button
                onClick={() => setActiveTab("admin_telemetry")}
                className={`nav-tab ${activeTab === "admin_telemetry" ? "active" : ""}`}
              >
                <span>System Telemetry</span>
              </button>
            </>
          )}

          {currentUser?.role === "RESEARCHER" && (
            <>
              <button
                onClick={() => setActiveTab("research_benchmarks")}
                className={`nav-tab ${activeTab === "research_benchmarks" ? "active" : ""}`}
              >
                <span>Model Benchmarks</span>
              </button>
              <button
                onClick={() => setActiveTab("research_ablations")}
                className={`nav-tab ${activeTab === "research_ablations" ? "active" : ""}`}
              >
                <span>Ablation Studies</span>
              </button>
              <button
                onClick={() => setActiveTab("research_dataset")}
                className={`nav-tab ${activeTab === "research_dataset" ? "active" : ""}`}
              >
                <span>Dataset Provenance</span>
              </button>
            </>
          )}
        </nav>

        {/* Status & User Actions */}
        <div className="navbar-actions">
          {/* Health indicator */}
          <div
            className={`badge ${backendOnline ? "badge-success" : "badge-error"}`}
            style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: backendOnline ? "var(--status-success)" : "var(--status-error)",
              }}
            />
            <span style={{ fontSize: "0.7rem", fontWeight: 600 }}>
              {backendOnline ? "Engine Online" : "Engine Offline"}
            </span>
          </div>

          {currentUser ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <div className="user-profile-badge">
                <div className="user-avatar-circle">
                  {currentUser.full_name?.charAt(0) || currentUser.email.charAt(0).toUpperCase()}
                </div>
                <div style={{ textAlign: "left", lineHeight: 1.15 }}>
                  <div style={{ fontSize: "0.775rem", fontWeight: 700, color: "var(--text-main)" }}>
                    {currentUser.full_name}
                  </div>
                  <div style={{ fontSize: "0.675rem", color: "var(--text-secondary)" }}>
                    {getRoleLabel(currentUser.role)} {currentUser.institution ? `• ${currentUser.institution}` : ""}
                  </div>
                </div>
              </div>

              <button
                onClick={onLogout}
                className="btn btn-secondary btn-icon"
                title="Sign out"
                style={{ width: "32px", height: "32px" }}
              >
                <LogOut size={14} style={{ color: "var(--text-secondary)" }} />
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={() => onOpenAuth("login")}
                className="btn btn-secondary btn-sm"
              >
                Sign In
              </button>
              <button
                onClick={() => onOpenAuth("register")}
                className="btn btn-primary btn-sm"
              >
                Register
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
