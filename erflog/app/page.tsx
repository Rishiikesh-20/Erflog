"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "@/lib/AuthContext";
import { Bot, Sparkles, ArrowRight, Shield, Zap, Brain } from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7F5F0]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D95D39]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F5F0]">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `radial-gradient(circle at 25px 25px, #D95D39 2px, transparent 0)`,
              backgroundSize: "50px 50px",
            }}
          />
        </div>

        <div className="relative max-w-7xl mx-auto px-6 py-20">
          {/* Header */}
          <nav className="flex items-center justify-between mb-20">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-[#D95D39] rounded-xl flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-xl text-gray-900">Erflog</h1>
                <p className="text-xs text-gray-500">AI Career Platform</p>
              </div>
            </div>
            <button
              onClick={() => router.push("/login")}
              className="flex items-center gap-2 px-6 py-3 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors font-medium"
            >
              Sign In
              <ArrowRight className="w-4 h-4" />
            </button>
          </nav>

          {/* Hero Content */}
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#D95D39]/10 rounded-full text-[#D95D39] text-sm font-medium mb-6">
                <Sparkles className="w-4 h-4" />
                Powered by 6 AI Agents
              </div>

              <h2 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-6">
                Your AI Career
                <span className="text-[#D95D39]"> Assistant</span>
                <br />
                Works 24/7
              </h2>

              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                Let our AI agents continuously monitor the job market, track
                your GitHub activity, and find opportunities perfectly matched
                to your skills. No more manual job hunting.
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={() => router.push("/login")}
                  className="flex items-center justify-center gap-2 px-8 py-4 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors font-medium text-lg"
                >
                  Get Started Free
                  <ArrowRight className="w-5 h-5" />
                </button>
                <button
                  onClick={() => router.push("/login")}
                  className="flex items-center justify-center gap-2 px-8 py-4 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium text-lg"
                >
                  Watch Demo
                </button>
              </div>
            </motion.div>

            {/* Agent Visualization */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative"
            >
              <div className="bg-white rounded-3xl border border-gray-200 p-8 shadow-xl">
                <div className="flex items-center gap-3 mb-6">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 3,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                    className="w-12 h-12 bg-[#D95D39] rounded-xl flex items-center justify-center"
                  >
                    <Bot className="w-6 h-6 text-white" />
                  </motion.div>
                  <div>
                    <p className="font-semibold text-gray-900">
                      Multi-Agent System
                    </p>
                    <p className="text-sm text-gray-500">
                      Active and monitoring
                    </p>
                  </div>
                  <div className="ml-auto flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm text-green-600">Online</span>
                  </div>
                </div>

                <div className="space-y-3">
                  {[
                    {
                      name: "Agent 1: Perception",
                      desc: "Resume & GitHub Analysis",
                      active: true,
                    },
                    {
                      name: "Agent 2: Market Sentinel",
                      desc: "Job Market Scanning",
                      active: true,
                    },
                    {
                      name: "Agent 3: Strategist",
                      desc: "Match & Roadmap Generation",
                      active: true,
                    },
                    {
                      name: "Agent 4: Operative",
                      desc: "Resume Tailoring",
                      active: false,
                    },
                    {
                      name: "Agent 5: Interview Coach",
                      desc: "Mock Interviews",
                      active: false,
                    },
                    {
                      name: "Agent 6: Chat Assistant",
                      desc: "Interview Practice",
                      active: false,
                    },
                  ].map((agent, idx) => (
                    <motion.div
                      key={agent.name}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 + idx * 0.1 }}
                      className={`flex items-center gap-3 p-3 rounded-xl ${
                        agent.active
                          ? "bg-green-50 border border-green-200"
                          : "bg-gray-50"
                      }`}
                    >
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          agent.active ? "bg-green-500" : "bg-gray-300"
                        }`}
                      >
                        <Brain className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1">
                        <p
                          className={`text-sm font-medium ${
                            agent.active ? "text-green-900" : "text-gray-600"
                          }`}
                        >
                          {agent.name}
                        </p>
                        <p className="text-xs text-gray-500">{agent.desc}</p>
                      </div>
                      {agent.active && (
                        <span className="text-xs text-green-600 font-medium">
                          Running
                        </span>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h3 className="text-3xl font-bold text-gray-900 mb-4">
              How Erflog Works
            </h3>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Our AI-powered platform automates your job search from start to
              finish
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Shield,
                title: "Smart Onboarding",
                desc: "Upload your resume or enter your skills manually. Our AI extracts and validates your expertise.",
              },
              {
                icon: Zap,
                title: "24/7 Job Matching",
                desc: "AI agents continuously scan the market to find jobs that match your skills and career goals.",
              },
              {
                icon: Brain,
                title: "Growth Tracking",
                desc: "We monitor your GitHub activity to track skill development and update your profile automatically.",
              },
            ].map((feature, idx) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                className="bg-gray-50 rounded-2xl p-8 hover:shadow-lg transition-shadow"
              >
                <div className="w-14 h-14 bg-[#D95D39]/10 rounded-xl flex items-center justify-center mb-6">
                  <feature.icon className="w-7 h-7 text-[#D95D39]" />
                </div>
                <h4 className="text-xl font-semibold text-gray-900 mb-3">
                  {feature.title}
                </h4>
                <p className="text-gray-600">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h3 className="text-4xl font-bold text-gray-900 mb-6">
              Ready to Transform Your Job Search?
            </h3>
            <p className="text-xl text-gray-600 mb-8">
              Join thousands of professionals who let AI do the heavy lifting
            </p>
            <button
              onClick={() => router.push("/login")}
              className="inline-flex items-center gap-2 px-10 py-5 bg-[#D95D39] text-white rounded-xl hover:bg-[#c54d2d] transition-colors font-medium text-lg"
            >
              Start Your Free Account
              <ArrowRight className="w-5 h-5" />
            </button>
          </motion.div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-10 h-10 bg-[#D95D39] rounded-xl flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl">Erflog</span>
          </div>
          <p className="text-gray-400 text-sm">
            © 2026 Erflog. AI-powered career intelligence platform.
          </p>
        </div>
      </footer>
    </div>
  );
}
