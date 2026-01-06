"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/lib/AuthContext";
import {
  Upload,
  FileText,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Github,
  Linkedin,
  GraduationCap,
  Target,
  Sparkles,
  Loader2,
  X,
  Plus,
  Edit3,
  Brain,
  Zap,
  Trophy,
  Code,
} from "lucide-react";
import * as api from "@/lib/api";
import type { EducationItem, QuizQuestion, QuizAnswer } from "@/lib/api";

// Step Indicator Component
function StepIndicator({
  currentStep,
  totalSteps,
}: {
  currentStep: number;
  totalSteps: number;
}) {
  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {Array.from({ length: totalSteps }, (_, i) => (
        <div
          key={i}
          className={`h-2 rounded-full transition-all duration-300 ${
            i + 1 === currentStep
              ? "w-8 bg-[#D95D39]"
              : i + 1 < currentStep
              ? "w-2 bg-green-500"
              : "w-2 bg-gray-300"
          }`}
        />
      ))}
    </div>
  );
}

// Skill Tag Input Component
function SkillTagInput({
  skills,
  setSkills,
  placeholder = "Add a skill...",
}: {
  skills: string[];
  setSkills: (skills: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");

  const addSkill = () => {
    const trimmed = input.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill));
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && (e.preventDefault(), addSkill())
          }
          placeholder={placeholder}
          className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
        />
        <button
          type="button"
          onClick={addSkill}
          className="px-4 py-3 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span
            key={skill}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 rounded-full text-sm"
          >
            {skill}
            <button
              type="button"
              onClick={() => removeSkill(skill)}
              className="hover:text-red-500 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

// Education Entry Component
function EducationEntry({
  education,
  onChange,
  onRemove,
}: {
  education: EducationItem;
  onChange: (edu: EducationItem) => void;
  onRemove: () => void;
}) {
  return (
    <div className="p-4 border border-gray-200 rounded-xl space-y-3 relative">
      <button
        type="button"
        onClick={onRemove}
        className="absolute top-3 right-3 text-gray-400 hover:text-red-500 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
      <div className="grid grid-cols-2 gap-3">
        <input
          type="text"
          value={education.institution || ""}
          onChange={(e) =>
            onChange({ ...education, institution: e.target.value })
          }
          placeholder="College/University"
          className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
        />
        <input
          type="text"
          value={education.degree || ""}
          onChange={(e) => onChange({ ...education, degree: e.target.value })}
          placeholder="Degree (e.g., B.Tech)"
          className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
        />
        <input
          type="text"
          value={education.course || ""}
          onChange={(e) => onChange({ ...education, course: e.target.value })}
          placeholder="Course (e.g., Computer Science)"
          className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
        />
        <input
          type="text"
          value={education.year || ""}
          onChange={(e) => onChange({ ...education, year: e.target.value })}
          placeholder="Year (e.g., 2024)"
          className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
        />
      </div>
    </div>
  );
}

// Quiz Question Card Component
function QuizCard({
  question,
  selectedIndex,
  onSelect,
  questionNumber,
  showResult,
}: {
  question: QuizQuestion;
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  questionNumber: number;
  showResult: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-full bg-[#D95D39]/10 flex items-center justify-center text-[#D95D39] font-semibold text-sm">
          {questionNumber}
        </div>
        <span className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
          {question.skill_being_tested}
        </span>
      </div>
      <p className="text-gray-900 font-medium mb-4">{question.question}</p>
      <div className="space-y-2">
        {question.options.map((option, idx) => {
          const isSelected = selectedIndex === idx;
          const isCorrect = idx === question.correct_index;

          let bgColor = "bg-gray-50 hover:bg-gray-100";
          let borderColor = "border-gray-200";

          if (showResult && isSelected) {
            bgColor = isCorrect ? "bg-green-50" : "bg-red-50";
            borderColor = isCorrect ? "border-green-500" : "border-red-500";
          } else if (showResult && isCorrect) {
            bgColor = "bg-green-50";
            borderColor = "border-green-500";
          } else if (isSelected) {
            bgColor = "bg-[#D95D39]/10";
            borderColor = "border-[#D95D39]";
          }

          return (
            <button
              key={idx}
              type="button"
              onClick={() => !showResult && onSelect(idx)}
              disabled={showResult}
              className={`w-full p-3 text-left rounded-xl border-2 transition-all ${bgColor} ${borderColor} ${
                showResult ? "cursor-default" : "cursor-pointer"
              }`}
            >
              <span className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-white border border-gray-300 flex items-center justify-center text-xs font-medium">
                  {String.fromCharCode(65 + idx)}
                </span>
                <span className="text-sm text-gray-700">{option}</span>
                {showResult && isCorrect && (
                  <CheckCircle2 className="w-4 h-4 text-green-500 ml-auto" />
                )}
              </span>
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();

  // Onboarding state
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1: Resume
  const [hasResume, setHasResume] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [extractedData, setExtractedData] = useState<{
    name?: string;
    email?: string;
    skills: string[];
    education: Array<{ institution: string; degree: string }>;
    experience_summary?: string;
  } | null>(null);

  // Step 2: Profile data (editable)
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [education, setEducation] = useState<EducationItem[]>([
    { institution: "", degree: "", course: "", year: "" },
  ]);
  const [experienceSummary, setExperienceSummary] = useState("");

  // Step 3: Social links
  const [githubUrl, setGithubUrl] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [leetcodeUrl, setLeetcodeUrl] = useState("");

  // Step 4: Quiz
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, number>>({});
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizResult, setQuizResult] = useState<{
    score: number;
    correct: number;
    total: number;
    message: string;
  } | null>(null);

  // Cold start progress state
  const [coldStartStatus, setColdStartStatus] = useState<
    "idle" | "processing" | "ready" | "error"
  >("idle");
  const [coldStartProgress, setColdStartProgress] = useState(0);
  const progressMessages = [
    "🔍 Scanning job listings...",
    "🎯 Finding your best matches...",
    "📊 Analyzing skill gaps...",
    "🗺️ Generating personalized roadmaps...",
    "✨ Preparing your dashboard...",
  ];

  // Check onboarding status on mount
  useEffect(() => {
    const checkStatus = async () => {
      if (!isAuthenticated) return;

      try {
        const status = await api.getOnboardingStatus();

        if (!status.needs_onboarding) {
          // Already completed onboarding, redirect to dashboard
          router.push("/dashboard");
          return;
        }

        // Set initial step based on status
        if (status.onboarding_step) {
          setStep(status.onboarding_step);
        }

        // Pre-fill email from auth
        if (user?.email) {
          setEmail(user.email);
        }

        // Try to get existing profile data
        try {
          const profileRes = await api.getUserProfile();
          if (profileRes.profile) {
            const p = profileRes.profile;
            if (p.name) setName(p.name);
            if (p.email) setEmail(p.email);
            if (p.skills && p.skills.length > 0) setSkills(p.skills);
            if (p.experience_summary)
              setExperienceSummary(p.experience_summary);
          }
        } catch {
          // Profile doesn't exist yet, that's fine
        }

        setIsLoading(false);
      } catch (err) {
        console.error("Failed to check onboarding status:", err);
        setIsLoading(false);
      }
    };

    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else {
        checkStatus();
      }
    }
  }, [isAuthenticated, authLoading, router, user]);

  // Handle resume upload
  const handleResumeUpload = async (file: File) => {
    setResumeFile(file);
    setIsUploading(true);
    setError(null);

    try {
      const response = await api.uploadResumePerception(file);

      if (response.status === "success" && response.data) {
        setHasResume(true);
        setExtractedData({
          name: response.data.name,
          email: response.data.email,
          skills: response.data.skills || [],
          education: response.data.education || [],
          experience_summary: response.data.experience_summary,
        });

        // Pre-fill form with extracted data
        if (response.data.name) setName(response.data.name);
        if (response.data.email) setEmail(response.data.email);
        if (response.data.skills) setSkills(response.data.skills);
        if (response.data.education) {
          setEducation(
            response.data.education.map((e) => ({
              institution: e.institution,
              degree: e.degree,
              course: "",
              year: "",
            }))
          );
        }
        if (response.data.experience_summary) {
          setExperienceSummary(response.data.experience_summary);
        }
      }
    } catch (err) {
      setError("Failed to upload resume. Please try again.");
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
      handleResumeUpload(file);
    } else {
      setError("Please upload a PDF file");
    }
  }, []);

  // Save profile data
  const saveProfile = async () => {
    if (!name.trim()) {
      setError("Please enter your name");
      return false;
    }
    if (skills.length === 0) {
      setError("Please add at least one skill");
      return false;
    }
    if (targetRoles.length === 0) {
      setError("Please add at least one target role");
      return false;
    }
    if (!education[0]?.institution || !education[0]?.degree) {
      setError("Please add your education details");
      return false;
    }

    setIsSaving(true);
    setError(null);

    try {
      await api.completeOnboarding({
        name,
        email: email || undefined,
        skills,
        target_roles: targetRoles,
        education: education.filter((e) => e.institution && e.degree),
        experience_summary: experienceSummary || undefined,
        github_url: githubUrl || undefined,
        linkedin_url: linkedinUrl || undefined,
        leetcode_url: leetcodeUrl || undefined,
        has_resume: hasResume,
      });
      return true;
    } catch (err) {
      setError("Failed to save profile. Please try again.");
      console.error(err);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  // Generate quiz questions
  const generateQuiz = async () => {
    setIsGeneratingQuiz(true);
    setError(null);

    try {
      const response = await api.generateOnboardingQuiz(skills, targetRoles);
      if (response.questions) {
        setQuizQuestions(response.questions);
      }
    } catch (err) {
      setError("Failed to generate quiz. Please try again.");
      console.error(err);
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  // Submit quiz
  const submitQuiz = async () => {
    const answers: QuizAnswer[] = quizQuestions.map((q) => ({
      question_id: q.id,
      selected_index: quizAnswers[q.id] ?? -1,
      correct_index: q.correct_index,
    }));

    setIsSaving(true);
    setError(null);

    try {
      const result = await api.submitOnboardingQuiz(answers);
      setQuizResult({
        score: result.score,
        correct: result.correct,
        total: result.total,
        message: result.message,
      });
      setQuizSubmitted(true);

      // Trigger cold start if backend signals to do so
      if (result.trigger_cold_start) {
        setColdStartStatus("processing");
        setColdStartProgress(0);

        try {
          // Trigger cold start in background
          await api.triggerColdStart();

          // Animate progress through messages
          for (let i = 0; i < progressMessages.length; i++) {
            setColdStartProgress(i);
            await new Promise((resolve) => setTimeout(resolve, 6000)); // ~30 seconds total
          }

          setColdStartStatus("ready");
        } catch (err) {
          console.error("Cold start failed:", err);
          setColdStartStatus("error");
          // Still allow user to proceed even if cold start fails
        }
      }
    } catch (err) {
      setError("Failed to submit quiz. Please try again.");
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  // Navigation
  const nextStep = async () => {
    if (step === 2) {
      // Save profile before moving to step 3
      const saved = await saveProfile();
      if (!saved) return;
    }

    if (step === 3) {
      // Save social links and generate quiz
      await saveProfile();
      setStep(4);
      generateQuiz();
      return;
    }

    setStep(step + 1);
    setError(null);
  };

  const prevStep = () => {
    setStep(step - 1);
    setError(null);
  };

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7F5F0]">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-[#D95D39] mx-auto mb-4" />
          <p className="text-gray-600">Setting up your workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F5F0] py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome to Erflog
          </h1>
          <p className="text-gray-600">
            Let&apos;s set up your AI-powered career profile
          </p>
        </motion.div>

        {/* Step Indicator */}
        <StepIndicator currentStep={step} totalSteps={4} />

        {/* Error Display */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Step Content */}
        <AnimatePresence mode="wait">
          {/* Step 1: Resume Upload (Optional) */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-[#D95D39]/10 flex items-center justify-center">
                  <FileText className="w-6 h-6 text-[#D95D39]" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Upload Your Resume
                  </h2>
                  <p className="text-sm text-gray-500">
                    Optional - We&apos;ll extract your skills automatically
                  </p>
                </div>
              </div>

              {!hasResume ? (
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-[#D95D39] transition-colors cursor-pointer"
                  onClick={() =>
                    document.getElementById("resume-input")?.click()
                  }
                >
                  {isUploading ? (
                    <div className="space-y-3">
                      <Loader2 className="w-12 h-12 mx-auto text-[#D95D39] animate-spin" />
                      <p className="text-gray-600">
                        Analyzing your resume with AI...
                      </p>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                      <p className="text-gray-600 mb-2">
                        Drag and drop your resume here, or click to browse
                      </p>
                      <p className="text-sm text-gray-400">PDF files only</p>
                    </>
                  )}
                  <input
                    id="resume-input"
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleResumeUpload(file);
                    }}
                  />
                </div>
              ) : (
                <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                  <CheckCircle2 className="w-12 h-12 mx-auto text-green-500 mb-3" />
                  <p className="text-green-700 font-medium mb-2">
                    Resume uploaded successfully!
                  </p>
                  <p className="text-sm text-green-600">
                    Extracted {extractedData?.skills.length || 0} skills
                  </p>
                </div>
              )}

              <div className="flex justify-between mt-8">
                <button
                  onClick={() => setStep(2)}
                  className="text-gray-500 hover:text-gray-700 transition-colors text-sm"
                >
                  Skip for now →
                </button>
                <button
                  onClick={nextStep}
                  disabled={!hasResume && !resumeFile}
                  className="flex items-center gap-2 px-6 py-3 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 2: Profile Details */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-[#D95D39]/10 flex items-center justify-center">
                  <Edit3 className="w-6 h-6 text-[#D95D39]" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Your Profile
                  </h2>
                  <p className="text-sm text-gray-500">
                    {hasResume
                      ? "Review and edit extracted data"
                      : "Enter your details"}
                  </p>
                </div>
              </div>

              <div className="space-y-6">
                {/* Name & Email */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="john@example.com"
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
                    />
                  </div>
                </div>

                {/* Skills */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <span className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#D95D39]" />
                      Skills *
                    </span>
                  </label>
                  <SkillTagInput
                    skills={skills}
                    setSkills={setSkills}
                    placeholder="Add skill (e.g., Python, React, AWS)"
                  />
                </div>

                {/* Target Roles */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <span className="flex items-center gap-2">
                      <Target className="w-4 h-4 text-[#D95D39]" />
                      Target Roles *
                    </span>
                  </label>
                  <SkillTagInput
                    skills={targetRoles}
                    setSkills={setTargetRoles}
                    placeholder="Add target role (e.g., Software Engineer, Data Scientist)"
                  />
                </div>

                {/* Education */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <span className="flex items-center gap-2">
                      <GraduationCap className="w-4 h-4 text-[#D95D39]" />
                      Education *
                    </span>
                  </label>
                  <div className="space-y-3">
                    {education.map((edu, idx) => (
                      <EducationEntry
                        key={idx}
                        education={edu}
                        onChange={(updated) => {
                          const newEdu = [...education];
                          newEdu[idx] = updated;
                          setEducation(newEdu);
                        }}
                        onRemove={() => {
                          if (education.length > 1) {
                            setEducation(education.filter((_, i) => i !== idx));
                          }
                        }}
                      />
                    ))}
                    <button
                      type="button"
                      onClick={() =>
                        setEducation([
                          ...education,
                          { institution: "", degree: "", course: "", year: "" },
                        ])
                      }
                      className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-[#D95D39] hover:text-[#D95D39] transition-colors flex items-center justify-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      Add Education
                    </button>
                  </div>
                </div>

                {/* Experience Summary (Optional) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Experience Summary (Optional)
                  </label>
                  <textarea
                    value={experienceSummary}
                    onChange={(e) => setExperienceSummary(e.target.value)}
                    placeholder="Brief summary of your professional experience..."
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39] resize-none"
                  />
                </div>
              </div>

              <div className="flex justify-between mt-8">
                <button
                  onClick={prevStep}
                  className="flex items-center gap-2 px-6 py-3 text-gray-600 hover:text-gray-900 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </button>
                <button
                  onClick={nextStep}
                  disabled={isSaving}
                  className="flex items-center gap-2 px-6 py-3 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors disabled:opacity-50"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      Continue
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 3: Social Links */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-[#D95D39]/10 flex items-center justify-center">
                  <Github className="w-6 h-6 text-[#D95D39]" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Connect Your Profiles
                  </h2>
                  <p className="text-sm text-gray-500">
                    Optional - Helps us track your growth
                  </p>
                </div>
              </div>

              <div className="space-y-6">
                {/* GitHub URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <span className="flex items-center gap-2">
                      <Github className="w-4 h-4" />
                      GitHub Profile
                    </span>
                  </label>
                  <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-[#D95D39]/20 focus-within:border-[#D95D39]">
                    <span className="px-4 py-3 bg-gray-50 text-gray-600 font-medium text-sm whitespace-nowrap border-r border-gray-200">
                      https://github.com/
                    </span>
                    <input
                      type="text"
                      value={githubUrl}
                      onChange={(e) => setGithubUrl(e.target.value)}
                      placeholder="username"
                      className="flex-1 px-4 py-3 border-none focus:outline-none"
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    We&apos;ll monitor your commits to track skill development
                  </p>
                </div>

                {/* LinkedIn URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <span className="flex items-center gap-2">
                      <Linkedin className="w-4 h-4" />
                      LinkedIn Profile
                    </span>
                  </label>
                  <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-[#D95D39]/20 focus-within:border-[#D95D39]">
                    <span className="px-4 py-3 bg-gray-50 text-gray-600 font-medium text-sm whitespace-nowrap border-r border-gray-200">
                      https://linkedin.com/in/
                    </span>
                    <input
                      type="text"
                      value={linkedinUrl}
                      onChange={(e) => setLinkedinUrl(e.target.value)}
                      placeholder="username"
                      className="flex-1 px-4 py-3 border-none focus:outline-none"
                    />
                  </div>
                </div>

                {/* LeetCode URL (Optional) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <span className="flex items-center gap-2">
                      <Code className="w-4 h-4" />
                      LeetCode Profile (Optional)
                    </span>
                  </label>
                  <input
                    type="url"
                    value={leetcodeUrl}
                    onChange={(e) => setLeetcodeUrl(e.target.value)}
                    placeholder="https://leetcode.com/u/username"
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39]"
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Connect to track your DSA progress and get personalized recommendations.
                  </p>
                </div>

                {/* Info Card */}
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <Brain className="w-5 h-5 text-blue-500 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-900">
                        Why connect profiles?
                      </p>
                      <p className="text-sm text-blue-700 mt-1">
                        Our AI continuously monitors your GitHub activity to
                        detect new skills and update your profile automatically.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between mt-8">
                <button
                  onClick={prevStep}
                  className="flex items-center gap-2 px-6 py-3 text-gray-600 hover:text-gray-900 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </button>
                <button
                  onClick={nextStep}
                  disabled={isSaving}
                  className="flex items-center gap-2 px-6 py-3 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors disabled:opacity-50"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      Continue to Quiz
                      <Zap className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 4: Quiz */}
          {step === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              {/* Quiz Header */}
              <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-[#D95D39]/10 flex items-center justify-center">
                    <Brain className="w-6 h-6 text-[#D95D39]" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">
                      Quick Assessment
                    </h2>
                    <p className="text-sm text-gray-500">
                      5 questions to verify your skills
                    </p>
                  </div>
                </div>
              </div>

              {/* Quiz Questions or Loading */}
              {isGeneratingQuiz ? (
                <div className="bg-white rounded-2xl border border-gray-200 p-12 shadow-sm text-center">
                  <Loader2 className="w-12 h-12 mx-auto text-[#D95D39] animate-spin mb-4" />
                  <p className="text-gray-600">
                    Generating personalized questions based on your skills...
                  </p>
                </div>
              ) : quizSubmitted && quizResult ? (
                <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm text-center">
                  <Trophy className="w-16 h-16 mx-auto text-[#D95D39] mb-4" />
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">
                    {quizResult.message}
                  </h3>
                  <p className="text-lg text-gray-600 mb-6">
                    Score: {quizResult.correct}/{quizResult.total} (
                    {quizResult.score.toFixed(0)}%)
                  </p>

                  {/* Cold Start Progress */}
                  {coldStartStatus === "processing" && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mb-6 p-4 bg-gradient-to-r from-[#D95D39]/10 to-purple-100 rounded-xl border border-[#D95D39]/20"
                    >
                      <div className="flex items-center justify-center gap-3 mb-3">
                        <Loader2 className="w-5 h-5 animate-spin text-[#D95D39]" />
                        <span className="text-sm font-medium text-gray-700">
                          Setting up your personalized experience...
                        </span>
                      </div>
                      <motion.p
                        key={coldStartProgress}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -5 }}
                        className="text-lg font-medium text-[#D95D39]"
                      >
                        {progressMessages[coldStartProgress]}
                      </motion.p>
                      {/* Progress bar */}
                      <div className="mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-[#D95D39] to-purple-500"
                          initial={{ width: "0%" }}
                          animate={{
                            width: `${((coldStartProgress + 1) / progressMessages.length) * 100}%`,
                          }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </motion.div>
                  )}

                  {coldStartStatus === "ready" && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="mb-6 p-4 bg-green-50 rounded-xl border border-green-200"
                    >
                      <CheckCircle2 className="w-8 h-8 mx-auto text-green-500 mb-2" />
                      <p className="text-green-700 font-medium">
                        Your personalized dashboard is ready!
                      </p>
                    </motion.div>
                  )}

                  {coldStartStatus === "error" && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mb-6 p-3 bg-yellow-50 rounded-xl border border-yellow-200 text-sm text-yellow-700"
                    >
                      We&apos;re still setting up your data. Your dashboard will be
                      fully personalized shortly!
                    </motion.div>
                  )}

                  <button
                    onClick={() => router.push("/dashboard")}
                    disabled={coldStartStatus === "processing"}
                    className="inline-flex items-center gap-2 px-8 py-4 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors text-lg font-medium disabled:opacity-50 disabled:cursor-wait"
                  >
                    {coldStartStatus === "processing" ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Preparing Dashboard...
                      </>
                    ) : (
                      <>
                        Go to Dashboard
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <>
                  <div className="space-y-4 mb-6">
                    {quizQuestions.map((q, idx) => (
                      <QuizCard
                        key={q.id}
                        question={q}
                        selectedIndex={quizAnswers[q.id] ?? null}
                        onSelect={(index) =>
                          setQuizAnswers({ ...quizAnswers, [q.id]: index })
                        }
                        questionNumber={idx + 1}
                        showResult={false}
                      />
                    ))}
                  </div>

                  <div className="flex justify-between">
                    <button
                      onClick={prevStep}
                      className="flex items-center gap-2 px-6 py-3 text-gray-600 hover:text-gray-900 transition-colors"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      Back
                    </button>
                    <button
                      onClick={submitQuiz}
                      disabled={
                        isSaving ||
                        Object.keys(quizAnswers).length < quizQuestions.length
                      }
                      className="flex items-center gap-2 px-8 py-3 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          Submit Quiz
                          <CheckCircle2 className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
