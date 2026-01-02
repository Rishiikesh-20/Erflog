"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/lib/SessionContext";
import { generateKit, getErrorMessage } from "@/lib/api";
import { Loader2, Download, Copy, Check, AlertCircle, ExternalLink } from "lucide-react";

export default function ApplyPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { profile, strategyJobs, sessionId } = useSession();

  // Find job from strategy jobs
  const job = strategyJobs.find((j) => j.id === jobId) || {
    title: "Job Position",
    company: "Company",
    description: "",
  };

  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  const [generationSuccess, setGenerationSuccess] = useState(false);

  const [formData, setFormData] = useState({
    whyJoin: "",
    shortDescription: "",
    additionalInfo: "",
  });

  const [copied, setCopied] = useState<string | null>(null);

  const handleGenerateKit = async () => {
    if (!profile) {
      setError("No profile found. Please upload your resume first on the home page.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGeneratedPdfUrl(null);
    setGenerationSuccess(false);

    try {
      const result = await generateKit(
        profile.name, 
        job.title, 
        job.company, 
        sessionId || undefined,
        job.description || undefined
      );

      if (result instanceof Blob) {
        // Direct PDF blob - download immediately
        const url = window.URL.createObjectURL(result);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Resume_${job.company.replace(/\s+/g, "_")}_${job.title
          .replace(/\s+/g, "_")
          .substring(0, 20)}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        setGenerationSuccess(true);
      } else {
        // JSON response - check for pdf_url
        const jsonResult = result as { 
          status?: string; 
          message?: string; 
          detail?: string;
          data?: { 
            pdf_url?: string; 
            pdf_path?: string;
          };
        };
        
        if (jsonResult.status === "success" && jsonResult.data?.pdf_url) {
          setGeneratedPdfUrl(jsonResult.data.pdf_url);
          setGenerationSuccess(true);
        } else {
          setError(jsonResult.message || jsonResult.detail || "Failed to generate resume.");
        }
      }
    } catch (err) {
      const errorMsg = getErrorMessage(err);
      if (errorMsg.includes("501") || errorMsg.includes("Not Implemented")) {
        setError("Please upload your resume on the home page first to enable resume generation.");
      } else {
        setError(errorMsg);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadPdf = () => {
    if (generatedPdfUrl) {
      // Open in new tab or trigger download
      window.open(generatedPdfUrl, '_blank');
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCopy = (field: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(null), 2000);
  };

  // Sample AI-generated responses
  const generatedResponses = {
    whyJoin: `I am excited about the opportunity to join ${job.company} because of its innovative approach to technology and commitment to excellence. The ${job.title} role aligns perfectly with my career aspirations and technical expertise. I am particularly drawn to the company's culture of continuous learning and the opportunity to work on impactful projects that make a real difference.`,
    shortDescription: `I am a passionate software engineer with hands-on experience in building scalable applications and solving complex technical challenges. My background includes working with cross-functional teams to deliver high-quality solutions on time. I thrive in collaborative environments and am constantly seeking to expand my technical knowledge and contribute meaningfully to team success.`,
    additionalInfo: `Throughout my career, I have demonstrated strong problem-solving abilities and a commitment to writing clean, maintainable code. I am experienced in agile methodologies and have a track record of quickly adapting to new technologies and frameworks. I am confident that my skills and enthusiasm would make me a valuable addition to the ${job.company} team.`,
  };

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
          <h1 className="font-serif-bold text-4xl text-ink mb-3">
            Apply to {job.company}
          </h1>
          <p className="text-xl text-secondary">{job.title}</p>
        </div>

        {/* Resume Download Section */}
        <div
          className="bg-surface rounded-xl border p-8 mb-8"
          style={{ borderColor: "#E5E0D8" }}
        >
          <div className="flex items-start gap-6">
            <div
              className="w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: generationSuccess ? "#22c55e" : "#D95D39" }}
            >
              {generationSuccess ? (
                <Check className="w-8 h-8 text-white" />
              ) : (
                <Download className="w-8 h-8 text-white" />
              )}
            </div>
            <div className="flex-1">
              <h2 className="font-serif-bold text-2xl text-ink mb-2">
                {generationSuccess ? "Resume Generated!" : "Your Optimized Resume"}
              </h2>
              <p className="text-secondary mb-6">
                {generationSuccess 
                  ? `Your tailored resume for ${job.company} is ready for download.`
                  : `Generate a tailored resume highlighting the skills and experiences most relevant to this position at ${job.company}.`
                }
              </p>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                {!generationSuccess ? (
                  <button
                    onClick={handleGenerateKit}
                    disabled={isGenerating || !profile}
                    className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                    style={{ backgroundColor: "#D95D39" }}
                  >
                    {isGenerating ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Download className="w-5 h-5" />
                    )}
                    {isGenerating ? "Generating..." : "Generate Tailored Resume"}
                  </button>
                ) : (
                  <>
                    {generatedPdfUrl && (
                      <button
                        onClick={handleDownloadPdf}
                        className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90"
                        style={{ backgroundColor: "#22c55e" }}
                      >
                        <Download className="w-5 h-5" />
                        Download Resume PDF
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setGenerationSuccess(false);
                        setGeneratedPdfUrl(null);
                      }}
                      className="inline-flex items-center gap-3 px-6 py-3 rounded-lg font-medium border transition-all hover:bg-gray-50"
                      style={{ borderColor: "#E5E0D8" }}
                    >
                      <Download className="w-5 h-5" />
                      Generate New Version
                    </button>
                  </>
                )}
              </div>

              {generatedPdfUrl && (
                <div className="mt-4 p-3 rounded-lg bg-green-50 border border-green-200">
                  <p className="text-sm text-green-700 flex items-center gap-2">
                    <Check className="w-4 h-4" />
                    Resume saved to cloud storage
                    <a 
                      href={generatedPdfUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="ml-2 underline flex items-center gap-1"
                    >
                      Open in new tab <ExternalLink className="w-3 h-3" />
                    </a>
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Application Questions Section */}
        <div
          className="bg-surface rounded-xl border p-8"
          style={{ borderColor: "#E5E0D8" }}
        >
          <h2 className="font-serif-bold text-2xl text-ink mb-6">
            Application Responses
          </h2>
          <p className="text-secondary mb-8">
            Use these AI-generated responses for common application questions.
            Click the copy button to copy to clipboard, or edit as needed.
          </p>

          {/* Why do you want to join */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <label className="font-serif-bold text-lg text-ink">
                Why do you want to join {job.company}?
              </label>
              <button
                onClick={() =>
                  handleCopy("whyJoin", formData.whyJoin || generatedResponses.whyJoin)
                }
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                {copied === "whyJoin" ? (
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
              value={formData.whyJoin || generatedResponses.whyJoin}
              onChange={(e) => handleInputChange("whyJoin", e.target.value)}
              rows={5}
              className="w-full px-4 py-3 rounded-lg border bg-white text-ink resize-none focus:outline-none focus:ring-2"
              style={{ borderColor: "#E5E0D8" } as React.CSSProperties}
            />
          </div>

          {/* Short Description */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <label className="font-serif-bold text-lg text-ink">
                Your Short Description
              </label>
              <button
                onClick={() =>
                  handleCopy("shortDescription", formData.shortDescription || generatedResponses.shortDescription)
                }
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                {copied === "shortDescription" ? (
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
              value={formData.shortDescription || generatedResponses.shortDescription}
              onChange={(e) => handleInputChange("shortDescription", e.target.value)}
              rows={5}
              className="w-full px-4 py-3 rounded-lg border bg-white text-ink resize-none focus:outline-none focus:ring-2"
              style={{ borderColor: "#E5E0D8" } as React.CSSProperties}
            />
          </div>

          {/* Additional Information */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <label className="font-serif-bold text-lg text-ink">
                Additional Information
              </label>
              <button
                onClick={() =>
                  handleCopy("additionalInfo", formData.additionalInfo || generatedResponses.additionalInfo)
                }
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                {copied === "additionalInfo" ? (
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
              value={formData.additionalInfo || generatedResponses.additionalInfo}
              onChange={(e) => handleInputChange("additionalInfo", e.target.value)}
              rows={5}
              className="w-full px-4 py-3 rounded-lg border bg-white text-ink resize-none focus:outline-none focus:ring-2"
              style={{ borderColor: "#E5E0D8" } as React.CSSProperties}
            />
          </div>

          {/* Tips Section */}
          <div className="p-5 rounded-lg bg-orange-50 border" style={{ borderColor: "#D95D39" }}>
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: "#D95D39" }} />
              <div>
                <h4 className="font-medium text-ink mb-1">Pro Tips</h4>
                <ul className="text-sm text-secondary space-y-1">
                  <li>• Personalize responses with specific examples from your experience</li>
                  <li>• Mention specific projects or technologies that align with the job</li>
                  <li>• Keep your responses concise but impactful</li>
                  <li>• Research {job.company} to add company-specific details</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8">
          <button
            onClick={() => router.back()}
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
