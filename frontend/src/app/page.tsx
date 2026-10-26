"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { AuthModal } from "../components/AuthModal";
import { TeacherDashboard } from "../components/TeacherDashboard";
import { AdminDashboard } from "../components/AdminDashboard";
import { ResearcherDashboard } from "../components/ResearcherDashboard";
import { api } from "../services/api";
import { User } from "../types";

export default function Home() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>("teacher_papers");
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login");
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);

  // Check health and current active session on mount
  useEffect(() => {
    const initialize = async () => {
      try {
        await api.getHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }

      // Check if user has an existing verified session
      try {
        const user = await api.getMe();
        setCurrentUser(user);
        if (user.role === "TEACHER") setActiveTab("teacher_papers");
        else if (user.role === "ADMIN") setActiveTab("admin_users");
        else if (user.role === "RESEARCHER") setActiveTab("research_benchmarks");
      } catch {
        setCurrentUser(null);
        setActiveTab("landing");
      } finally {
        setInitialLoading(false);
      }
    };

    initialize();
  }, []);

  const handleOpenAuth = (mode: "login" | "register" = "login") => {
    setAuthModalMode(mode);
    setShowAuthModal(true);
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setActiveTab("landing");
  };

  return (
    <div className="app-shell">
      {/* Top Navigation */}
      <Navbar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAuth={handleOpenAuth}
        onLogout={handleLogout}
        backendOnline={backendOnline}
      />

      {/* Main Content */}
      <main className="content-wrapper" style={{ flex: 1 }}>
        {initialLoading ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh" }}>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Loading platform...
            </p>
          </div>
        ) : !currentUser || activeTab === "landing" ? (
          /* Clean Institutional Portal */
          <div style={{ maxWidth: "980px", margin: "2rem auto", padding: "0 1rem" }}>
            {/* Simple, focused hero */}
            <div style={{ textAlign: "center", marginBottom: "3rem" }}>
              <div
                className="badge badge-jade"
                style={{
                  display: "inline-block",
                  padding: "0.3rem 0.85rem",
                  borderRadius: "20px",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  marginBottom: "1rem",
                }}
              >
                Institutional Examination Assessment
              </div>

              <h1 style={{ fontSize: "2.25rem", color: "var(--text-main)", marginBottom: "0.85rem", lineHeight: 1.25 }}>
                Examination Paper Difficulty & Cognitive Demand Analyzer
              </h1>

              <p style={{ fontSize: "1rem", color: "var(--text-secondary)", maxWidth: "700px", margin: "0 auto 1.75rem auto", lineHeight: 1.5 }}>
                An educational evaluation platform analyzing examination question papers across revised Bloom’s Taxonomy cognitive levels and empirical difficulty with human-in-the-loop review.
              </p>

              <div style={{ display: "flex", justifyContent: "center", gap: "0.75rem" }}>
                <button
                  onClick={() => handleOpenAuth("login")}
                  className="btn btn-primary"
                  style={{ padding: "0.65rem 1.25rem", fontSize: "0.9rem" }}
                >
                  Sign In to Workspace
                </button>
                <button
                  onClick={() => handleOpenAuth("register")}
                  className="btn btn-secondary"
                  style={{ padding: "0.65rem 1.25rem", fontSize: "0.9rem" }}
                >
                  Register College / Institution
                </button>
              </div>
            </div>

            {/* Core Features */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
              <div className="academic-card" style={{ padding: "1.5rem" }}>
                <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Faculty & Educators</h3>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
                  Upload PDF and Word examination papers. Extract questions, review automated Bloom’s Taxonomy and difficulty classifications, and download institutional PDF and CSV reports.
                </p>
                <button
                  onClick={() => handleOpenAuth("login")}
                  className="btn btn-outline btn-sm"
                  style={{ width: "100%" }}
                >
                  Faculty Login
                </button>
              </div>

              <div className="academic-card" style={{ padding: "1.5rem" }}>
                <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Institutional Governance</h3>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
                  Manage verified faculty and researcher accounts, audit document processing, and inspect server runtime health and PostgreSQL database connectivity.
                </p>
                <button
                  onClick={() => handleOpenAuth("login")}
                  className="btn btn-outline btn-sm"
                  style={{ width: "100%" }}
                >
                  Administrator Login
                </button>
              </div>

              <div className="academic-card" style={{ padding: "1.5rem" }}>
                <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Empirical Research & Benchmarks</h3>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "1rem" }}>
                  Evaluate held-out test splits, inspect multi-modal feature ablation studies, and review classification confusion matrices.
                </p>
                <button
                  onClick={() => handleOpenAuth("login")}
                  className="btn btn-outline btn-sm"
                  style={{ width: "100%" }}
                >
                  Researcher Login
                </button>
              </div>
            </div>
          </div>
        ) : currentUser.role === "TEACHER" || activeTab.startsWith("teacher") ? (
          <TeacherDashboard activeTab={activeTab} onTabChange={setActiveTab} />
        ) : currentUser.role === "ADMIN" || activeTab.startsWith("admin") ? (
          <AdminDashboard />
        ) : (
          <ResearcherDashboard />
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid var(--border-light)", backgroundColor: "var(--bg-surface)", padding: "1rem 1.5rem", marginTop: "auto" }}>
        <div style={{ maxWidth: "1400px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            <strong>Question Paper Difficulty Analyzer</strong> — Institutional Examination Demand & Cognitive Level Evaluation
          </div>
          <div style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
            PostgreSQL / MySQL Database • Zero Mock Data
          </div>
        </div>
      </footer>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={showAuthModal}
        initialMode={authModalMode}
        onClose={() => setShowAuthModal(false)}
        onSuccess={(user) => {
          setCurrentUser(user);
          if (user.role === "TEACHER") setActiveTab("teacher_papers");
          else if (user.role === "ADMIN") setActiveTab("admin_users");
          else if (user.role === "RESEARCHER") setActiveTab("research_benchmarks");
        }}
      />
    </div>
  );
}
