"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "@/lib/AuthContext";
import * as api from "@/lib/api";
import {
  Save,
  Upload,
  Github,
  Linkedin,
  FileText,
  User,
  Settings as SettingsIcon,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  RefreshCw,
} from "lucide-react";

export default function Settings() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, signOut } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Profile state
  const [profile, setProfile] = useState<api.SettingsProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");

  // Update states
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const [isCalculatingAts, setIsCalculatingAts] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch profile on mount
  useEffect(() => {
    const fetchProfile = async () => {
      if (!isAuthenticated) return;

      try {
        const data = await api.getSettingsProfile();
        setProfile(data.profile);
        setName(data.profile.name || "");
        setGithubUrl(data.profile.github_url || "");
        setLinkedinUrl(data.profile.linkedin_url || "");
        
        // If ATS score is null but user has a resume, calculate it on demand
        if (!data.profile.ats_score && data.profile.resume_url) {
          console.log("ATS score is null, calculating on demand...");
          setIsCalculatingAts(true);
          try {
            const atsResult = await api.calculateAtsOnDemand();
            if (atsResult.ats_score) {
              setProfile(prev => prev ? { ...prev, ats_score: atsResult.ats_score } : null);
              console.log("ATS score calculated:", atsResult.ats_score);
            }
          } catch (atsErr) {
            console.error("Failed to calculate ATS score:", atsErr);
            // Don't show error to user, ATS is optional
          } finally {
            setIsCalculatingAts(false);
          }
        }
      } catch (err) {
        console.error("Failed to fetch profile:", err);
        setError("Failed to load profile. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else {
        fetchProfile();
      }
    }
  }, [isAuthenticated, authLoading, router]);

  // Handle profile update
  const handleSaveProfile = async () => {
    setIsSavingProfile(true);
    setSuccessMessage(null);
    setError(null);

    try {
      const updateData: api.ProfileUpdateRequest = {};
      
      if (name !== profile?.name) updateData.name = name;
      if (githubUrl !== profile?.github_url) updateData.github_url = githubUrl;
      if (linkedinUrl !== profile?.linkedin_url) updateData.linkedin_url = linkedinUrl;

      if (Object.keys(updateData).length === 0) {
        setSuccessMessage("No changes to save");
        setIsSavingProfile(false);
        return;
      }

      const result = await api.updateProfile(updateData);
      setSuccessMessage(result.message);
      
      // Refresh profile
      const data = await api.getSettingsProfile();
      setProfile(data.profile);
    } catch (err: any) {
      console.error("Failed to update profile:", err);
      setError(err.response?.data?.detail || "Failed to update profile");
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handle resume upload
  const handleResumeUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are allowed");
      return;
    }

    setIsUploadingResume(true);
    setSuccessMessage(null);
    setError(null);

    try {
      const result = await api.updatePrimaryResume(file);
      setSuccessMessage(result.message);
      
      // Refresh profile
      const data = await api.getSettingsProfile();
      setProfile(data.profile);
    } catch (err: any) {
      console.error("Failed to upload resume:", err);
      setError(err.response?.data?.detail || "Failed to upload resume");
    } finally {
      setIsUploadingResume(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7F5F0]">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-14 h-14 bg-[#D95D39] rounded-xl flex items-center justify-center mx-auto mb-4"
          >
            <SettingsIcon className="w-7 h-7 text-white" />
          </motion.div>
          <p className="text-gray-600">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F5F0] py-12 px-8">
      <div className="max-w-2xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="font-serif text-4xl font-bold text-gray-900 mb-2">
            Settings
          </h1>
          <p className="text-gray-600 mb-8">
            Configure your Erflog experience and manage your profile.
          </p>
        </motion.div>

        {/* Success/Error Messages */}
        {successMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3"
          >
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            <p className="text-green-800">{successMessage}</p>
          </motion.div>
        )}

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-800">{error}</p>
          </motion.div>
        )}

        <div className="space-y-6">
          {/* Profile Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-[#D95D39]/10 rounded-xl flex items-center justify-center">
                <User className="w-5 h-5 text-[#D95D39]" />
              </div>
              <div>
                <h2 className="font-semibold text-lg text-gray-900">Profile Information</h2>
                <p className="text-sm text-gray-500">Update your basic information</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39] focus:border-transparent text-gray-900"
                  placeholder="Your full name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={profile?.email || ""}
                  disabled
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                  placeholder="Email from authentication"
                />
                <p className="text-xs text-gray-400 mt-1">Email is managed by your authentication provider</p>
              </div>
            </div>
          </motion.div>

          {/* Social Links Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
                <Github className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="font-semibold text-lg text-gray-900">Social Links</h2>
                <p className="text-sm text-gray-500">Connect your professional profiles</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  GitHub URL
                </label>
                <div className="relative">
                  <Github className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="url"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39] focus:border-transparent text-gray-900"
                    placeholder="https://github.com/username"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  LinkedIn URL
                </label>
                <div className="relative">
                  <Linkedin className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#D95D39] focus:border-transparent text-gray-900"
                    placeholder="https://linkedin.com/in/username"
                  />
                </div>
              </div>
            </div>

            {/* Save Button */}
            <button
              onClick={handleSaveProfile}
              disabled={isSavingProfile}
              className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-[#D95D39] text-white rounded-lg font-medium hover:bg-[#c54d2d] transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {isSavingProfile ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  Save Changes
                </>
              )}
            </button>
          </motion.div>

          {/* Primary Resume Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                <FileText className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="font-semibold text-lg text-gray-900">Primary Resume</h2>
                <p className="text-sm text-gray-500">Your main resume used for profile analysis</p>
              </div>
            </div>

            {profile?.resume_url ? (
              <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-gray-600" />
                    <span className="text-sm text-gray-700">Current resume uploaded</span>
                  </div>
                  <a
                    href={profile.resume_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-[#D95D39] hover:underline"
                  >
                    View <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                
                
                {/* ATS Score Badge */}
                {isCalculatingAts ? (
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full flex items-center justify-center bg-blue-100">
                        <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">Calculating ATS Score...</p>
                        <p className="text-xs text-gray-500">Analyzing your resume compatibility</p>
                      </div>
                    </div>
                  </div>
                ) : profile.ats_score ? (
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
                    <div className="flex items-center gap-3">
                      <div 
                        className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg ${
                          parseInt(profile.ats_score) >= 70 
                            ? 'bg-green-500' 
                            : parseInt(profile.ats_score) >= 40 
                              ? 'bg-yellow-500' 
                              : 'bg-red-500'
                        }`}
                      >
                        {profile.ats_score}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">ATS Compatibility Score</p>
                        <p className="text-xs text-gray-500">
                          {parseInt(profile.ats_score) >= 70 
                            ? '✓ Great! Your resume is ATS-friendly' 
                            : parseInt(profile.ats_score) >= 40 
                              ? '⚠ Consider improving keywords' 
                              : '✗ Needs optimization for ATS'}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="p-4 bg-yellow-50 rounded-lg mb-4">
                <p className="text-sm text-yellow-700">No resume uploaded yet</p>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleResumeUpload}
              className="hidden"
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingResume}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 border-2 border-dashed border-gray-300 text-gray-700 rounded-lg font-medium hover:border-[#D95D39] hover:text-[#D95D39] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploadingResume ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  {profile?.resume_url ? "Upload New Resume" : "Upload Resume"}
                </>
              )}
            </button>
            <p className="text-xs text-gray-400 mt-2 text-center">
              PDF files only. This will replace your existing resume.
            </p>
          </motion.div>

          {/* Secondary/Tailored Resume Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
                <RefreshCw className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h2 className="font-semibold text-lg text-gray-900">Tailored Resume</h2>
                <p className="text-sm text-gray-500">AI-generated resume for job applications</p>
              </div>
            </div>

            {profile?.sec_resume_url ? (
              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-green-600" />
                  <span className="text-sm text-gray-700">Latest tailored resume available</span>
                </div>
                <a
                  href={profile.sec_resume_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-green-600 hover:underline"
                >
                  View <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ) : (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  No tailored resume yet. Generate one by clicking "Deploy" on a job in the Strategy Board!
                </p>
              </div>
            )}
          </motion.div>

          {/* About Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm"
          >
            <h2 className="font-semibold text-lg text-gray-900 mb-4">About Erflog</h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              Erflog is your personal career intelligence platform powered by
              advanced AI agent swarms. Our system analyzes job opportunities and
              creates personalized learning roadmaps to help you achieve your
              career goals.
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
