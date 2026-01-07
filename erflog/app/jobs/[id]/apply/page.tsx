"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { useSession } from "@/lib/SessionContext";
import { getTodayJobs, generateTailoredResume, autoApplyToJob, getSettingsProfile, findRecruiterEmail, TodayDataItem, RecruiterEmail } from "@/lib/api";
import {
  Loader2,
  Download,
  Copy,
  Check,
  AlertCircle,
  ExternalLink,
  FileText,
  Sparkles,
  Wand2,
  Bot,
  CheckCircle,
  XCircle,
  Mail,
  User,
} from "lucide-react";

export default function ApplyPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { sessionId } = useSession();

  // State for job data
  const [job, setJob] = useState<TodayDataItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State for resume generation
  const [resumeUrl, setResumeUrl] = useState<string | null>(null);
  const [isGeneratingResume, setIsGeneratingResume] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);

  // State for copied indicators
  const [copied, setCopied] = useState<string | null>(null);

  // State for auto-apply
  const [isAutoApplying, setIsAutoApplying] = useState(false);
  const [autoApplyResult, setAutoApplyResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // State for editable form data (initialized from pre-generated)
  const [formData, setFormData] = useState({
    whyCompany: "",
    whyRole: "",
    shortIntro: "",
    coverLetterOpening: "",
    coverLetterBody: "",
    coverLetterClosing: "",
  });

  // State for recruiter email finder
  const [isFindingRecruiter, setIsFindingRecruiter] = useState(false);
  const [recruiterEmails, setRecruiterEmails] = useState<RecruiterEmail[]>([]);
  const [emailTemplate, setEmailTemplate] = useState<string | null>(null);
  const [recruiterError, setRecruiterError] = useState<string | null>(null);

  // Fetch job data with pre-generated application text and resume
  useEffect(() => {
    const fetchJobData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await getTodayJobs();

        if (response.status === "success" && response.jobs) {
          // Find job by ID (handle both string and numeric formats)
          const foundJob = response.jobs.find((j) => {
            const jId = String(j.id).replace(".0", "");
            const targetId = String(jobId).replace(".0", "");
            return jId === targetId || j.id === jobId;
          });

          if (foundJob) {
            setJob(foundJob);

            // Initialize form data from pre-generated application text
            if (foundJob.application_text) {
              const appText = foundJob.application_text;
              setFormData({
                whyCompany: appText.why_this_company || "",
                whyRole: appText.why_this_role || "",
                shortIntro: appText.short_intro || "",
                coverLetterOpening: appText.cover_letter_opening || "",
                coverLetterBody: appText.cover_letter_body || "",
                coverLetterClosing: appText.cover_letter_closing || "",
              });
            }
          } else {
            setError(
              "Job not found. It may have been removed from today's matches."
            );
          }
        } else {
          setError("Failed to fetch job data.");
        }
      } catch (err) {
        console.error("Error fetching job:", err);
        setError("Failed to load job details. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchJobData();
  }, [jobId]);

  const handleCopy = (field: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleDownloadResume = () => {
    if (resumeUrl) {
      window.open(resumeUrl, "_blank");
    }
  };

  const handleGenerateResume = async () => {
    if (!job) return;

    setIsGeneratingResume(true);
    setResumeError(null);

    try {
      // Build job description for the API
      const jobDescription = `
Job Title: ${job.title}
Company: ${job.company}

Description:
${job.summary || ""}

Platform: ${job.platform || ""}
Location: ${job.location || ""}
      `.trim();

      const result = await generateTailoredResume(jobDescription, job.id);

      if (result.success && result.pdf_url) {
        setResumeUrl(result.pdf_url);
      } else {
        setResumeError(
          result.message || "Failed to generate resume. Please try again."
        );
      }
    } catch (err) {
      console.error("Resume generation error:", err);
      setResumeError(
        "Failed to generate resume. Please ensure you have uploaded your resume on the home page."
      );
    } finally {
      setIsGeneratingResume(false);
    }
  };

  const handleAutoApply = async () => {
    if (!job || !job.link) return;

    setIsAutoApplying(true);
    setAutoApplyResult(null);

    try {
      // Get user profile for form data
      const profileResponse = await getSettingsProfile();
      const profile = profileResponse.profile;

      // Build user data object for form filling
      const userData: Record<string, string> = {
        name: profile.name || "",
        email: profile.email || "",
        phone: "", // Not stored in profile
        linkedin: profile.linkedin_url || "",
        github: profile.github_url || "",
        location: "", // Not stored in profile
        skills: (profile.skills || []).join(", "),
      };

      const result = await autoApplyToJob(job.link, userData);

      setAutoApplyResult({
        success: result.success,
        message: result.message,
      });
    } catch (err) {
      console.error("Auto-apply error:", err);
      setAutoApplyResult({
        success: false,
        message: "Failed to start auto-apply. Please try again or apply manually.",
      });
    } finally {
      setIsAutoApplying(false);
    }
  };

  // Handler for finding recruiter emails
  const handleFindRecruiter = async () => {
    if (!job) return;

    setIsFindingRecruiter(true);
    setRecruiterError(null);
    setRecruiterEmails([]);
    setEmailTemplate(null);

    try {
      const result = await findRecruiterEmail(
        job.company,
        jobId,
        job.title
      );

      if (result.success) {
        setRecruiterEmails(result.emails);
        setEmailTemplate(result.email_template);
      } else {
        setRecruiterError("No recruiter emails found for this company.");
      }
    } catch (err: any) {
      console.error("Find recruiter error:", err);
      setRecruiterError(
        err?.response?.data?.detail || "Failed to find recruiter emails. Please try again."
      );
    } finally {
      setIsFindingRecruiter(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2
            className="w-12 h-12 animate-spin"
            style={{ color: "#D95D39" }}
          />
          <p className="text-secondary">Loading application kit...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !job) {
    return (
      <div className="min-h-screen bg-canvas py-12 px-8">
        <div className="max-w-2xl mx-auto text-center">
          <AlertCircle
            className="w-16 h-16 mx-auto mb-6"
            style={{ color: "#D95D39" }}
          />
          <h1 className="font-serif-bold text-3xl text-ink mb-4">
            Job Not Found
          </h1>
          <p className="text-secondary mb-8">
            {error || "The job you're looking for is not available."}
          </p>
          <button
            onClick={() => router.push("/jobs")}
            className="px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90"
            style={{ backgroundColor: "#D95D39" }}
          >
            Browse Jobs
          </button>
        </div>
      </div>
    );
  }

  const applicationText = job.application_text;

  return (
    <div className="min-h-screen bg-canvas py-12 px-8">
      {/* Back Button */}
      <button
        onClick={() => router.back()}
        className="mb-8 flex items-center gap-2 text-secondary hover:text-ink transition-colors"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Job Details
      </button>

      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <Sparkles className="w-8 h-8" style={{ color: "#D95D39" }} />
            <h1 className="font-serif-bold text-4xl text-ink">
              Application Kit
            </h1>
          </div>
          <p className="text-xl text-secondary">
            {job.title} at {job.company}
          </p>
          <p className="text-sm text-secondary mt-2">
            Match Score:{" "}
            <span
              className="font-medium"
              style={{ color: job.score >= 0.8 ? "#22c55e" : "#D95D39" }}
            >
              {(job.score * 100).toFixed(0)}%
            </span>
          </p>
        </div>

        {/* Tailored Resume Section */}
        <div
          className="bg-surface rounded-xl border p-8 mb-8"
          style={{ borderColor: "#E5E0D8" }}
        >
          <div className="flex items-start gap-6">
            <div
              className="w-16 h-16 rounded-xl flex items-center justify-center shrink-0"
              style={{
                backgroundColor: resumeUrl ? "#22c55e" : "#D95D39",
              }}
            >
              {isGeneratingResume ? (
                <Loader2 className="w-8 h-8 text-white animate-spin" />
              ) : (
                <FileText className="w-8 h-8 text-white" />
              )}
            </div>
            <div className="flex-1">
              <h2 className="font-serif-bold text-2xl text-ink mb-2">
                Tailored Resume
              </h2>
              <p className="text-secondary mb-6">
                {resumeUrl
                  ? `Your resume has been optimized for this ${job.title} position at ${job.company}. It highlights the most relevant skills and experiences.`
                  : `Generate a tailored resume optimized for this ${job.title} position. Our AI will rewrite your resume to highlight relevant skills and experiences.`}
              </p>

              {resumeError && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200">
                  <p className="text-sm text-red-700 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {resumeError}
                  </p>
                </div>
              )}

              {resumeUrl ? (
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleDownloadResume}
                    className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90"
                    style={{ backgroundColor: "#22c55e" }}
                  >
                    <Download className="w-5 h-5" />
                    Download Tailored Resume
                  </button>
                  <a
                    href={resumeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium border transition-all hover:bg-gray-50"
                    style={{ borderColor: "#E5E0D8" }}
                  >
                    <ExternalLink className="w-5 h-5" />
                    Open in New Tab
                  </a>
                  <button
                    onClick={() => {
                      setResumeUrl(null);
                      setResumeError(null);
                    }}
                    className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium border transition-all hover:bg-gray-50 text-secondary"
                    style={{ borderColor: "#E5E0D8" }}
                  >
                    <Wand2 className="w-5 h-5" />
                    Regenerate
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleGenerateResume}
                  disabled={isGeneratingResume}
                  className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ backgroundColor: "#D95D39" }}
                >
                  {isGeneratingResume ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Generating Resume...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-5 h-5" />
                      Generate Tailored Resume
                    </>
                  )}
                </button>
              )}

              {isGeneratingResume && (
                <div className="mt-4 p-4 rounded-lg bg-blue-50 border border-blue-200">
                  <p className="text-sm text-blue-700">
                    ⏳ This may take 15-30 seconds. We&apos;re analyzing your
                    resume and optimizing it for this specific job...
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Auto-Apply Section */}
        {job.link && (
          <div
            className="bg-surface rounded-xl border p-8 mb-8"
            style={{ borderColor: "#E5E0D8" }}
          >
            <div className="flex items-start gap-6">
              <div
                className="w-16 h-16 rounded-xl flex items-center justify-center shrink-0"
                style={{
                  backgroundColor: autoApplyResult?.success
                    ? "#22c55e"
                    : isAutoApplying
                    ? "#3b82f6"
                    : "#8b5cf6",
                }}
              >
                {isAutoApplying ? (
                  <Loader2 className="w-8 h-8 text-white animate-spin" />
                ) : (
                  <Bot className="w-8 h-8 text-white" />
                )}
              </div>
              <div className="flex-1">
                <h2 className="font-serif-bold text-2xl text-ink mb-2">
                  Auto-Apply (Beta)
                </h2>
                <p className="text-secondary mb-4">
                  Let our AI assistant open the job application page and auto-fill
                  the form with your profile information. You&apos;ll need to review
                  and submit manually.
                </p>

                {/* Warning Banner */}
                <div className="mb-6 p-4 rounded-lg bg-amber-50 border border-amber-200">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-amber-800">
                        Important: Review Before Submitting
                      </p>
                      <p className="text-sm text-amber-700 mt-1">
                        This feature will auto-fill the application form but will
                        NOT submit it. Always review the filled information before
                        manually submitting your application.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Result Feedback */}
                {autoApplyResult && (
                  <div
                    className={`mb-4 p-4 rounded-lg border ${
                      autoApplyResult.success
                        ? "bg-green-50 border-green-200"
                        : "bg-red-50 border-red-200"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {autoApplyResult.success ? (
                        <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                      )}
                      <p
                        className={`text-sm ${
                          autoApplyResult.success
                            ? "text-green-700"
                            : "text-red-700"
                        }`}
                      >
                        {autoApplyResult.message}
                      </p>
                    </div>
                  </div>
                )}

                {/* Auto-Apply Button */}
                <button
                  onClick={handleAutoApply}
                  disabled={isAutoApplying}
                  className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ backgroundColor: "#8b5cf6" }}
                >
                  {isAutoApplying ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Opening Browser & Filling Form...
                    </>
                  ) : (
                    <>
                      <Bot className="w-5 h-5" />
                      Auto-Fill Application
                    </>
                  )}
                </button>

                {isAutoApplying && (
                  <div className="mt-4 p-4 rounded-lg bg-blue-50 border border-blue-200">
                    <p className="text-sm text-blue-700">
                      🤖 A browser window will open on the server. The AI is
                      navigating to the job page and filling out the application
                      form. This may take 30-60 seconds...
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ==================== FIND RECRUITER EMAIL SECTION ==================== */}
        <div
          className="bg-surface rounded-xl border p-8 mb-8"
          style={{ borderColor: "#E5E0D8" }}
        >
          <div className="flex items-start gap-6">
            <div
              className="w-16 h-16 rounded-xl flex items-center justify-center shrink-0"
              style={{
                backgroundColor: recruiterEmails.length > 0
                  ? "#22c55e"
                  : isFindingRecruiter
                  ? "#3b82f6"
                  : "#ec4899",
              }}
            >
              {isFindingRecruiter ? (
                <Loader2 className="w-8 h-8 text-white animate-spin" />
              ) : (
                <Mail className="w-8 h-8 text-white" />
              )}
            </div>
            <div className="flex-1">
              <h2 className="font-serif-bold text-2xl text-ink mb-2">
                Find Recruiter Email
              </h2>
              <p className="text-secondary mb-4">
                Find HR and recruiter emails at {job?.company || "this company"} using Hunter.io.
                We&apos;ll also generate a personalized outreach email template for you.
              </p>

              {/* Error Message */}
              {recruiterError && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200">
                  <p className="text-sm text-red-700 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {recruiterError}
                  </p>
                </div>
              )}

              {/* Find Recruiter Button */}
              {recruiterEmails.length === 0 && !emailTemplate && (
                <button
                  onClick={handleFindRecruiter}
                  disabled={isFindingRecruiter}
                  className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ backgroundColor: "#ec4899" }}
                >
                  {isFindingRecruiter ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Finding Recruiters...
                    </>
                  ) : (
                    <>
                      <Mail className="w-5 h-5" />
                      Find Recruiter Emails
                    </>
                  )}
                </button>
              )}

              {/* Recruiter Emails Results */}
              {recruiterEmails.length > 0 && (
                <div className="space-y-4">
                  <h3 className="font-medium text-ink">Found {recruiterEmails.length} contact{recruiterEmails.length !== 1 ? 's' : ''}:</h3>
                  <div className="space-y-3">
                    {recruiterEmails.map((recruiter, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-4 rounded-lg border bg-white"
                        style={{ borderColor: "#E5E0D8" }}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-pink-100 flex items-center justify-center">
                            <User className="w-5 h-5 text-pink-600" />
                          </div>
                          <div>
                            <p className="font-medium text-ink">
                              {recruiter.full_name || "Unknown"}
                              {recruiter.is_recruiter && (
                                <span className="ml-2 px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                                  Recruiter
                                </span>
                              )}
                            </p>
                            <p className="text-sm text-secondary">
                              {recruiter.position || "Employee"} • {recruiter.email}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleCopy(`email-${idx}`, recruiter.email)}
                          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
                        >
                          {copied === `email-${idx}` ? (
                            <>
                              <Check className="w-4 h-4 text-green-600" />
                              <span className="text-green-600">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-4 h-4" />
                              Copy Email
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                </div>
                </div>
              )}

              {/* Email Template - Shows even if no emails found */}
              {emailTemplate && (
                <div className="mt-6">
                  {recruiterEmails.length === 0 && (
                    <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
                      <p className="text-sm text-amber-700">
                        ⚠️ No recruiter emails found in Hunter.io&apos;s database for this company. 
                        But here&apos;s a ready-to-use outreach template!
                      </p>
                    </div>
                  )}
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-ink">Outreach Email Template</h3>
                    <button
                      onClick={() => handleCopy("email-template", emailTemplate)}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-pink-100 hover:bg-pink-200 transition-colors text-pink-700"
                    >
                      {copied === "email-template" ? (
                        <>
                          <Check className="w-4 h-4" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Copy Template
                        </>
                      )}
                    </button>
                  </div>
                  <div
                    className="p-4 rounded-lg border bg-gradient-to-br from-pink-50 to-white whitespace-pre-wrap text-sm text-ink font-mono"
                    style={{ borderColor: "#E5E0D8" }}
                  >
                    {emailTemplate}
                  </div>

                  {/* Try Again Button */}
                  <button
                    onClick={handleFindRecruiter}
                    disabled={isFindingRecruiter}
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-all hover:bg-gray-50 text-secondary"
                    style={{ borderColor: "#E5E0D8" }}
                  >
                    <Mail className="w-4 h-4" />
                    Search Again
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Application Responses Section */}
        <div
          className="bg-surface rounded-xl border p-8"
          style={{ borderColor: "#E5E0D8" }}
        >
          <h2 className="font-serif-bold text-2xl text-ink mb-2">
            Pre-Generated Application Responses
          </h2>
          <p className="text-secondary mb-8">
            These responses were automatically generated based on your profile
            and this job. Click to copy, or edit as needed before using in your
            application.
          </p>

          {applicationText ? (
            <>
              {/* Why this company */}
              <ResponseField
                label={`Why do you want to join ${job.company}?`}
                value={formData.whyCompany}
                fieldKey="whyCompany"
                copied={copied}
                onCopy={handleCopy}
                onChange={handleInputChange}
              />

              {/* Why this role */}
              <ResponseField
                label={`Why are you interested in the ${job.title} role?`}
                value={formData.whyRole}
                fieldKey="whyRole"
                copied={copied}
                onCopy={handleCopy}
                onChange={handleInputChange}
              />

              {/* Short Intro */}
              <ResponseField
                label="Elevator Pitch / Short Introduction"
                value={formData.shortIntro}
                fieldKey="shortIntro"
                copied={copied}
                onCopy={handleCopy}
                onChange={handleInputChange}
              />

              {/* Cover Letter Opening */}
              <ResponseField
                label="Cover Letter - Opening Paragraph"
                value={formData.coverLetterOpening}
                fieldKey="coverLetterOpening"
                copied={copied}
                onCopy={handleCopy}
                onChange={handleInputChange}
              />

              {/* Cover Letter Body */}
              <ResponseField
                label="Cover Letter - Main Body"
                value={formData.coverLetterBody}
                fieldKey="coverLetterBody"
                copied={copied}
                onCopy={handleCopy}
                onChange={handleInputChange}
                rows={6}
              />

              {/* Cover Letter Closing */}
              <ResponseField
                label="Cover Letter - Closing Paragraph"
                value={formData.coverLetterClosing}
                fieldKey="coverLetterClosing"
                copied={copied}
                onCopy={handleCopy}
                onChange={handleInputChange}
              />

              {/* Key Achievements */}
              {applicationText.key_achievements &&
                applicationText.key_achievements.length > 0 && (
                  <div className="mb-8">
                    <div className="flex items-center justify-between mb-3">
                      <label className="font-serif-bold text-lg text-ink">
                        Key Achievements to Highlight
                      </label>
                      <button
                        onClick={() =>
                          handleCopy(
                            "achievements",
                            applicationText.key_achievements?.join("\n• ") || ""
                          )
                        }
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
                      >
                        {copied === "achievements" ? (
                          <>
                            <Check className="w-4 h-4 text-green-600" />
                            <span className="text-green-600">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy All
                          </>
                        )}
                      </button>
                    </div>
                    <ul
                      className="space-y-2 p-4 rounded-lg border bg-white"
                      style={{ borderColor: "#E5E0D8" }}
                    >
                      {applicationText.key_achievements.map(
                        (achievement, idx) => (
                          <li
                            key={idx}
                            className="flex items-start gap-2 text-ink"
                          >
                            <span className="text-green-600 mt-0.5">✓</span>
                            {achievement}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}

              {/* Questions for Interviewer */}
              {applicationText.questions_for_interviewer &&
                applicationText.questions_for_interviewer.length > 0 && (
                  <div className="mb-8">
                    <div className="flex items-center justify-between mb-3">
                      <label className="font-serif-bold text-lg text-ink">
                        Questions to Ask the Interviewer
                      </label>
                      <button
                        onClick={() =>
                          handleCopy(
                            "questions",
                            applicationText.questions_for_interviewer?.join(
                              "\n• "
                            ) || ""
                          )
                        }
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
                      >
                        {copied === "questions" ? (
                          <>
                            <Check className="w-4 h-4 text-green-600" />
                            <span className="text-green-600">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy All
                          </>
                        )}
                      </button>
                    </div>
                    <ul
                      className="space-y-2 p-4 rounded-lg border bg-white"
                      style={{ borderColor: "#E5E0D8" }}
                    >
                      {applicationText.questions_for_interviewer.map(
                        (question, idx) => (
                          <li
                            key={idx}
                            className="flex items-start gap-2 text-ink"
                          >
                            <span
                              style={{ color: "#D95D39" }}
                              className="mt-0.5"
                            >
                              ?
                            </span>
                            {question}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
            </>
          ) : (
            <div className="p-6 rounded-lg bg-yellow-50 border border-yellow-200 text-center">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 text-yellow-600" />
              <h3 className="font-medium text-ink mb-2">
                Application Responses Not Yet Generated
              </h3>
              <p className="text-sm text-yellow-700">
                Application responses will be generated during the next daily
                update. Check back later or browse other jobs.
              </p>
            </div>
          )}

          {/* Tips Section */}
          <div
            className="p-5 rounded-lg bg-orange-50 border mt-6"
            style={{ borderColor: "#D95D39" }}
          >
            <div className="flex items-start gap-3">
              <AlertCircle
                className="w-6 h-6 flex-shrink-0 mt-0.5"
                style={{ color: "#D95D39" }}
              />
              <div>
                <h4 className="font-medium text-ink mb-1">Pro Tips</h4>
                <ul className="text-sm text-secondary space-y-1">
                  <li>
                    • Personalize responses with specific examples from your
                    experience
                  </li>
                  <li>
                    • Mention specific projects or technologies that align with
                    the job
                  </li>
                  <li>• Keep your responses concise but impactful</li>
                  <li>
                    • Research {job.company} to add company-specific details
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* External Apply Button */}
        {job.link && (
          <div
            className="mt-8 p-6 bg-surface rounded-xl border text-center"
            style={{ borderColor: "#E5E0D8" }}
          >
            <h3 className="font-serif-bold text-xl text-ink mb-2">
              Ready to Apply?
            </h3>
            <p className="text-secondary mb-4">
              Use your tailored resume and responses to apply on the company
              website.
            </p>
            <a
              href={job.link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-3 px-8 py-4 rounded-lg font-medium text-white transition-all hover:opacity-90"
              style={{ backgroundColor: "#D95D39" }}
            >
              <ExternalLink className="w-5 h-5" />
              Apply on {job.platform || "Company Website"}
            </a>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8">
          <button
            onClick={() => router.push(`/jobs/${jobId}`)}
            className="flex-1 py-4 rounded-lg font-medium border transition-all hover:bg-gray-50"
            style={{ borderColor: "#E5E0D8" }}
          >
            Back to Job Details
          </button>
          <button
            onClick={() => router.push("/jobs")}
            className="flex-1 py-4 rounded-lg font-medium text-white transition-all hover:opacity-90"
            style={{ backgroundColor: "#D95D39" }}
          >
            Browse More Jobs
          </button>
        </div>
      </div>
    </div>
  );
}

// Reusable Response Field Component
function ResponseField({
  label,
  value,
  fieldKey,
  copied,
  onCopy,
  onChange,
  rows = 4,
}: {
  label: string;
  value: string;
  fieldKey: string;
  copied: string | null;
  onCopy: (field: string, text: string) => void;
  onChange: (field: string, value: string) => void;
  rows?: number;
}) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <label className="font-serif-bold text-lg text-ink">{label}</label>
        <button
          onClick={() => onCopy(fieldKey, value)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
        >
          {copied === fieldKey ? (
            <>
              <Check className="w-4 h-4 text-green-600" />
              <span className="text-green-600">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              Copy
            </>
          )}
        </button>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(fieldKey, e.target.value)}
        rows={rows}
        className="w-full px-4 py-3 rounded-lg border bg-white text-ink resize-none focus:outline-none focus:ring-2"
        style={{ borderColor: "#E5E0D8" } as React.CSSProperties}
        placeholder="No content generated yet..."
      />
    </div>
  );
}
