"use client"

import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Download, AlertCircle, Target, History, Zap, Award, BookOpen, MessageSquare, ChevronRight, Check, X, AlertTriangle, ArrowLeft, Clock, CheckCircle2, Brain, Quote, Lightbulb, Activity, BarChart, TrendingUp, Flag } from "lucide-react"
import { motion, Variants } from "framer-motion"
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts"

import Navigation from "../components/landing/Navigation"
import { getApiUrl } from "@/lib/api"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"

// --- TYPES & INTERFACES (UPDATED TO MATCH BACKEND) ---

interface BaseMeta {
    scenario_id: string
    outcome_status: string
    overall_grade: string
    summary: string
    scenario_type?: string
    session_mode?: string
    emotional_trajectory?: string
    session_quality?: string
    key_themes?: string[]
    scenario?: string
}

interface BehaviourItem {
    behavior: string
    quote: string
    insight: string
    impact: string
    improved_approach: string
}

interface DetailedAnalysisItem {
    topic: string
    analysis: string
}

interface ScorecardItem {
    dimension: string
    score: string
    description?: string // Keeping for backward compatibility
    reasoning?: string // New field for Proof of Marks
    quote?: string
    suggestion?: string
    alternative_questions?: { question: string; rationale: string }[]
}

interface GenericReportData {
    meta: BaseMeta
    type?: string
    transcript?: { role: "user" | "assistant", content: string }[]
    behaviour_analysis?: BehaviourItem[]
    detailed_analysis?: DetailedAnalysisItem[] | string
    question_analysis?: QuestionAnalysis // NEW: Enhanced question analysis
    [key: string]: any
}



// --- NEW DEFINITIONS FOR COACHING SIMULATION ---
interface ExecutiveSummary {
    snapshot: string;
    final_score: string;
    strengths_summary: string;
    improvements_summary: string;
    outcome_summary: string;
}

interface GoalAttainment {
    score: string;
    expectation_vs_reality: string;
    primary_gaps: string[];
    observation_focus: string[];
}

interface DeepDiveItem {
    topic: string;
    tone?: string;
    language_impact?: string;
    comfort_level?: string;
    impact?: string;
    questions_asked?: string;
    exploration?: string;
    understanding_depth?: string;
    analysis?: string; // fallback
}

interface ActionPlan {
    specific_actions: string[];
    owner: string;
    timeline: string;
    success_indicators: string[];
}

interface FollowUpStrategy {
    review_cadence: string;
    metrics_to_track: string[];
    accountability_method: string;
}

interface FinalEvaluation {
    readiness_level: string;
    maturity_rating: string;
    immediate_focus: string[];
    long_term_suggestion: string;
}

interface SimulationReportData extends GenericReportData {
    executive_summary?: ExecutiveSummary;
    goal_attainment?: GoalAttainment;
    deep_dive_analysis?: DeepDiveItem[]; // Override generic
    scorecard?: ScorecardItem[]; // using existing
    missed_opportunities?: string[];
    action_plan?: ActionPlan;
    follow_up_strategy?: FollowUpStrategy;
    strengths_and_improvements?: { strengths: string[]; missed_opportunities: string[] };
    final_evaluation?: FinalEvaluation;
    pattern_summary?: string;
    turning_points?: { point: string; timestamp: string }[];
    coaching_style?: { primary_style: string; description: string };
    heat_map?: { dimension: string; score: number }[];
    ideal_questions?: string[];
}

// Question Analysis (Backend Enhanced)
interface QuestionMissed {
    question: string
    category?: string // Discovery, Probing, Clarifying, Vision, Closing
    timing?: string // Early, Mid, Late
    why_important: string
    when_to_ask: string
    impact_if_asked: string
}

interface QuestionAnalysis {
    questions_asked_count: number
    questions_missed: QuestionMissed[]
    question_quality_score?: string
    question_quality_feedback?: string
    questioning_improvement_tip?: string
}

const containerVars: Variants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.1 }
    }
}

const itemVars: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 50 } }
}

export default function Report() {
    const params = useParams()
    const navigate = useNavigate()
    const sessionId = params.sessionId as string
    const [data, setData] = useState<GenericReportData | null>(null)
    const [loading, setLoading] = useState(true)
    const [showTranscript, setShowTranscript] = useState(false)

    useEffect(() => {
        const fetchReport = async () => {
            try {
                if (!sessionId) return

                const { data: { session } } = await supabase.auth.getSession();
                const headers: Record<string, string> = {
                    'Content-Type': 'application/json'
                };
                if (session?.access_token) {
                    headers['Authorization'] = `Bearer ${session.access_token}`;
                }

                const response = await fetch(getApiUrl(`/api/session/${sessionId}/report_data`), { headers })
                if (!response.ok) throw new Error("Failed to fetch report data")
                const data: GenericReportData = await response.json()
                setData(data)
                setLoading(false)
            } catch (err) {
                console.error("Error generating report:", err)
                setLoading(false)
            }
        }
        fetchReport()
    }, [sessionId])

    const handleDownload = async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const headers: Record<string, string> = {};
            if (session?.access_token) {
                headers['Authorization'] = `Bearer ${session.access_token}`;
            }

            const response = await fetch(getApiUrl(`/api/report/${sessionId}`), { headers })
            if (!response.ok) throw new Error("Failed to generate PDF")

            const contentType = response.headers.get('content-type') || ''

            // If backend returns a redirect URL (Blob Storage), open it directly
            if (contentType.includes('application/json')) {
                const jsonData = await response.json()
                if (jsonData.url) {
                    window.open(jsonData.url, '_blank')
                    return
                }
                throw new Error("No report URL found")
            }

            // Otherwise, handle as binary PDF
            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `CoActAI_Report_${sessionId}.pdf`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            window.URL.revokeObjectURL(url)
        } catch (error) {
            console.error("Error downloading PDF:", error)
            alert("PDF export failed. Please ensure the backend is running.")
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-6 font-sans">
                <div className="relative">
                    <div className="w-16 h-16 rounded-full border-4 border-primary/30 border-t-primary animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Zap className="w-6 h-6 text-primary animate-pulse" />
                    </div>
                </div>
                <p className="text-muted-foreground animate-pulse font-medium tracking-wide">GENERATING ANALYSIS...</p>
            </div>
        )
    }

    if (!data || !data.meta) {
        return (
            <div className="min-h-screen bg-background p-12 flex flex-col items-center justify-center font-sans">
                <AlertCircle className="h-16 w-16 text-amber-500 mb-6" />
                <h2 className="text-3xl font-bold text-foreground mb-3">Report Unavailable</h2>
                <Button onClick={() => navigate("/")} variant="secondary">Return Home</Button>
            </div>
        )
    }

    const renderContent = () => {
        // ALL assessment scenarios use the rich SimulationView template
        return <SimulationView data={data as SimulationReportData} />
    }

    return (
        <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30">
            <Navigation />
            <div className="fixed inset-0 pointer-events-none -z-10">
                <div className="absolute top-[-20%] right-[-10%] w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-20%] left-[-10%] w-[400px] h-[400px] bg-purple-600/5 rounded-full blur-[120px]" />
            </div>

            <main className="relative container mx-auto px-4 sm:px-6 py-24 sm:py-32 space-y-12">
                {/* HEADER & BANNER */}
                <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                    <div className="flex flex-col md:flex-row gap-8 justify-between items-start">
                        <div>
                            <button onClick={() => navigate('/history')} className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 group">
                                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                                Back to History
                            </button>
                            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                                <div>
                                    <div className="flex items-center gap-3 mb-2">
                                        <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
                                            {data.meta.scenario_type || 'Custom Scenario'}
                                        </span>
                                        {data.meta.session_mode && (
                                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${data.meta.session_mode === 'skill_assessment'
                                                ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                                                : data.meta.session_mode === 'practice'
                                                    ? 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                                                    : 'bg-purple-500/10 text-purple-600 border-purple-500/20'
                                                }`}>
                                                {data.meta.session_mode.replace('_', ' ')}
                                            </span>
                                        )}
                                        <span className="text-muted-foreground text-sm font-medium flex items-center gap-1">
                                            <Clock className="w-3.5 h-3.5" />
                                            {new Date().toLocaleDateString()}
                                        </span>
                                    </div>
                                    <h1 className="text-4xl md:text-5xl font-black text-foreground mb-2">Session Analysis</h1>
                                    <p className="text-xl text-muted-foreground">{data.meta.summary}</p>
                                </div>
                            </div>
                        </div>
                        <div className="flex flex-col items-end gap-4 min-w-[200px]">
                            <div className="text-right">
                                <div className="text-sm font-bold text-muted-foreground uppercase tracking-widest mb-1">Overall Grade</div>
                                <div className={`text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br from-blue-400 to-indigo-500 leading-none`}>
                                    {data.meta.overall_grade}
                                </div>
                            </div>
                            <Button onClick={handleDownload} variant="outline" className="gap-2 border-border hover:bg-accent w-full">
                                <Download className="w-4 h-4" /> Export PDF Report
                            </Button>
                        </div>
                    </div>

                    {/* METRICS BANNER (Matches PDF Banner) */}
                    <div className="grid md:grid-cols-3 gap-6">
                        {data.meta.emotional_trajectory && (
                            <GlassCard className="p-4 flex flex-col bg-indigo-500/5 border-indigo-500/10">
                                <span className="text-xs font-bold text-indigo-500 uppercase tracking-wider mb-2">Emotional Arc</span>
                                <span className="text-sm font-medium text-foreground">{data.meta.emotional_trajectory}</span>
                            </GlassCard>
                        )}
                        {data.meta.session_quality && (
                            <GlassCard className="p-4 flex flex-col bg-emerald-500/5 border-emerald-500/10">
                                <span className="text-xs font-bold text-emerald-500 uppercase tracking-wider mb-2">Session Quality</span>
                                <span className="text-sm font-medium text-foreground">{data.meta.session_quality}</span>
                            </GlassCard>
                        )}
                        {data.meta.key_themes && (
                            <GlassCard className="p-4 flex flex-col bg-pink-500/5 border-pink-500/10">
                                <span className="text-xs font-bold text-pink-500 uppercase tracking-wider mb-2">Key Themes</span>
                                <div className="flex flex-wrap gap-2">
                                    {data.meta.key_themes.slice(0, 3).map((t, i) => (
                                        <span key={i} className="text-xs bg-background/50 px-2 py-1 rounded border border-border/50">{t}</span>
                                    ))}
                                </div>
                            </GlassCard>
                        )}
                    </div>
                </motion.div>


                <motion.div variants={containerVars} initial="hidden" animate="show">
                    {renderContent()}
                </motion.div>

                {/* TRANSCRIPT */}
                {data.transcript && (
                    <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="rounded-3xl bg-card border border-border overflow-hidden backdrop-blur-sm">
                        <div className="px-8 py-6 flex items-center justify-between cursor-pointer hover:bg-accent transition-colors group" onClick={() => setShowTranscript(!showTranscript)}>
                            <div className="flex items-center gap-4">
                                <div className="p-3 rounded-xl bg-primary/10 transition-colors group-hover:bg-primary/20 text-primary"><History className="w-5 h-5" /></div>
                                <div>
                                    <h3 className="text-lg font-bold text-foreground">Session Transcript</h3>
                                    <p className="text-sm text-muted-foreground">Review the full conversation log</p>
                                </div>
                            </div>
                            <ChevronRight className={`w-5 h-5 text-muted-foreground transition-transform ${showTranscript ? 'rotate-90' : ''}`} />
                        </div>
                        {showTranscript && (
                            <div className="p-8 max-h-[600px] overflow-y-auto space-y-6 border-t border-border bg-muted/20">
                                {data.transcript?.map((msg, idx) => (
                                    <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`p-4 rounded-2xl max-w-[80%] text-sm leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-br-none' : 'bg-card text-foreground border border-border rounded-bl-none'}`}>
                                            {msg.content}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </motion.div>
                )}
            </main>
        </div>
    )
}

// --- SHARED COMPONENTS ---

const GlassCard = ({ children, className = "" }: any) => (
    <motion.div variants={itemVars} className={`bg-card rounded-2xl border border-border p-6 shadow-sm ${className}`}>{children}</motion.div>
)

const SectionHeader = ({ icon: Icon, title, colorClass = "text-primary", bgClass = "bg-primary/10" }: any) => (
    <div className="flex items-center gap-4 mb-6">
        <div className={`p-3 rounded-xl ${bgClass} ring-1 ring-border/50`}><Icon className={`w-6 h-6 ${colorClass}`} /></div>
        <h2 className="text-xl font-bold text-foreground tracking-wide uppercase">{title}</h2>
    </div>
)

const ProgressBar = ({ value, colorClass = "bg-primary" }: { value: number, colorClass?: string }) => (
    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
        <motion.div initial={{ width: 0 }} whileInView={{ width: `${value}%` }} transition={{ duration: 1 }} className={`h-full ${colorClass}`} />
    </div>
)



const ScenarioContextSection = ({ scenario }: { scenario: string }) => {
    // Clean up scenario text similar to PDF logic
    const cleanScenario = (scenario || "")
        .replace(/CONTEXT:/g, "")
        .replace(/Situation:/g, "")
        .replace(/AI BEHAVIOR:[\s\S]*/g, "") // Remove AI Behavior section
        .replace(/AI ROLE:[\s\S]*/g, "")
        .replace(/USER ROLE:[\s\S]*/g, "")
        .trim();

    return (
        <GlassCard className="bg-slate-50 dark:bg-slate-900 border-l-4 border-l-primary/50">
            <SectionHeader icon={BookOpen} title="Scenario Context" colorClass="text-slate-500" bgClass="bg-slate-500/10" />
            <p className="text-base text-foreground/80 leading-relaxed font-serif italic">
                "{cleanScenario}"
            </p>
        </GlassCard>
    )
}

const EQAnalysisSection = ({ items }: { items?: { nuance: string; proof?: string; observation?: string; suggestion: string }[] }) => {
    if (!items || items.length === 0) return null
    return (
        <GlassCard>
            <SectionHeader icon={Brain} title="Emotional Intelligence (EQ) & Nuance" colorClass="text-pink-500" bgClass="bg-pink-500/10" />
            <div className="space-y-6">
                {items.map((item, i) => (
                    <div key={i} className="p-4 rounded-xl bg-pink-500/5 border border-pink-500/10">
                        <h3 className="font-bold text-lg text-pink-600 mb-2">{item.nuance}</h3>
                        <div className="space-y-3">
                            {(item.proof || item.observation) && (
                                <div className="flex gap-2 text-sm text-foreground/80">
                                    <span className="font-bold text-xs uppercase text-slate-500 mt-1">Proof:</span>
                                    <span className="italic">"{(item.proof || item.observation)}"</span>
                                </div>
                            )}
                            {item.suggestion && (
                                <div className="flex gap-2 text-sm text-foreground/80">
                                    <span className="font-bold text-xs uppercase text-slate-500 mt-1">Suggestion:</span>
                                    <span>{item.suggestion}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </GlassCard>
    )
}

const BehaviourAnalysisSection = ({ items }: { items?: BehaviourItem[] }) => {
    if (!items || items.length === 0) return null
    return (
        <GlassCard className="col-span-full">
            <SectionHeader icon={Brain} title="Behavioral Analysis" colorClass="text-purple-500" bgClass="bg-purple-500/10" />
            <div className="space-y-6">
                {items.map((item, i) => (
                    <div key={i} className="flex flex-col md:flex-row gap-6 p-6 rounded-xl bg-background border border-border hover:shadow-md transition-shadow">
                        <div className="flex-1 space-y-3">
                            <div className="flex items-center gap-3">
                                <h3 className="font-bold text-lg text-foreground">{item.behavior}</h3>
                                <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${item.impact.toLowerCase().includes('positive') ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                                    {item.impact}
                                </span>
                            </div>
                            <p className="text-muted-foreground leading-relaxed">{item.insight}</p>
                            {item.quote && (
                                <div className="flex gap-3 text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg border-l-4 border-primary/20 italic">
                                    <Quote className="w-4 h-4 shrink-0 opacity-50" /> "{item.quote}"
                                </div>
                            )}
                        </div>
                        {item.improved_approach && (
                            <div className="md:w-1/3 bg-blue-500/5 border border-blue-500/10 p-5 rounded-lg">
                                <h4 className="flex items-center gap-2 text-xs font-bold text-blue-500 uppercase tracking-wider mb-3">
                                    <Lightbulb className="w-4 h-4" /> Try This Instead
                                </h4>
                                <p className="text-sm text-foreground/90 leading-relaxed font-medium">{item.improved_approach}</p>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </GlassCard>
    )
}

const DetailedAnalysisSection = ({ items }: { items?: DetailedAnalysisItem[] | string }) => {
    if (!items) return null
    return (
        <GlassCard>
            <SectionHeader icon={BookOpen} title="Deep Dive Analysis" colorClass="text-indigo-500" bgClass="bg-indigo-500/10" />
            <div className="space-y-6">
                {Array.isArray(items) ? items.map((item, i) => (
                    <div key={i} className="space-y-2">
                        <h3 className="font-bold text-foreground border-l-4 border-indigo-500 pl-3">{item.topic}</h3>
                        <p className="text-muted-foreground leading-relaxed pl-4">{item.analysis}</p>
                    </div>
                )) : (
                    <p className="text-muted-foreground leading-relaxed">{items}</p>
                )}
            </div>
        </GlassCard>
    )
}

const SkillRadarChart = ({ items }: { items: { dimension: string; score: number | string }[] }) => {
    const data = items.map(item => ({
        subject: item.dimension,
        A: typeof item.score === 'number' ? item.score : parseFloat(item.score.split('/')[0]) || 0,
        fullMark: 10
    }))

    return (
        <div className="w-full h-[300px] flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
                    <PolarGrid stroke="currentColor" className="text-muted-foreground/20" />
                    <PolarAngleAxis
                        dataKey="subject"
                        tick={{ fill: 'currentColor', fontSize: 10, fontWeight: 600 }}
                        className="text-muted-foreground"
                    />
                    <Radar
                        name="Score"
                        dataKey="A"
                        stroke="#a855f7"
                        fill="#a855f7"
                        fillOpacity={0.3}
                    />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    )
}

const CompetencyHeatMap = ({ items }: { items: { dimension: string; score: number }[] }) => {
    const getScoreColor = (score: number) => {
        if (score >= 8) return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 ring-emerald-500/30'
        if (score >= 5) return 'bg-amber-500/10 text-amber-600 border-amber-500/20 ring-amber-500/30'
        return 'bg-rose-500/10 text-rose-600 border-rose-500/20 ring-rose-500/30'
    }

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item, i) => (
                <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className={`p-5 rounded-2xl border flex flex-col items-center justify-center gap-2 group hover:shadow-lg transition-all duration-300 ring-1 ${getScoreColor(item.score)}`}
                >
                    <div className="text-[10px] font-black uppercase tracking-[0.2em] opacity-60 text-center leading-tight">
                        {item.dimension}
                    </div>
                    <div className="text-4xl font-black tracking-tighter group-hover:scale-110 transition-transform">
                        {item.score}
                    </div>
                    <div className="w-full h-1 bg-current/10 rounded-full mt-2 overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            whileInView={{ width: `${(item.score / 10) * 100}%` }}
                            transition={{ duration: 1, delay: 0.5 }}
                            className="h-full bg-current"
                        />
                    </div>
                </motion.div>
            ))}
        </div>
    )
}

// Enhanced Questions Section
const QuestionsSection = ({ analysis }: { analysis?: QuestionAnalysis }) => {
    if (!analysis || !analysis.questions_missed || analysis.questions_missed.length === 0) return null

    // Group questions by timing
    const questionsByTiming = {
        Early: analysis.questions_missed.filter(q => q.timing === 'Early'),
        Mid: analysis.questions_missed.filter(q => q.timing === 'Mid'),
        Late: analysis.questions_missed.filter(q => q.timing === 'Late'),
        Uncategorized: analysis.questions_missed.filter(q => !q.timing)
    }

    const getCategoryColor = (category?: string) => {
        switch (category) {
            case 'Discovery': return 'bg-blue-500/10 text-blue-600 border-blue-500/20'
            case 'Probing': return 'bg-purple-500/10 text-purple-600 border-purple-500/20'
            case 'Clarifying': return 'bg-amber-500/10 text-amber-600 border-amber-500/20'
            case 'Vision': return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
            case 'Closing': return 'bg-rose-500/10 text-rose-600 border-rose-500/20'
            default: return 'bg-slate-500/10 text-slate-600 border-slate-500/20'
        }
    }

    const getTimingColor = (timing?: string) => {
        switch (timing) {
            case 'Early': return 'bg-green-500/10 text-green-700'
            case 'Mid': return 'bg-yellow-500/10 text-yellow-700'
            case 'Late': return 'bg-orange-500/10 text-orange-700'
            default: return 'bg-gray-500/10 text-gray-700'
        }
    }

    return (
        <GlassCard className="border-l-4 border-l-primary">
            <SectionHeader icon={MessageSquare} title="Questions You Should Have Asked" colorClass="text-primary" bgClass="bg-primary/10" />

            {/* Quality Score Summary */}
            {analysis.question_quality_score && (
                <div className="mb-6 p-4 rounded-xl bg-primary/5 border border-primary/10">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Question Quality Score</span>
                        <span className="text-2xl font-black text-primary">{analysis.question_quality_score}</span>
                    </div>
                    {analysis.question_quality_feedback && (
                        <p className="text-sm text-foreground/80 mb-2">{analysis.question_quality_feedback}</p>
                    )}
                    {analysis.questioning_improvement_tip && (
                        <div className="flex gap-2 items-start mt-3 p-3 bg-blue-500/5 rounded-lg border border-blue-500/10">
                            <Lightbulb className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                            <span className="text-sm text-foreground/90 font-medium">{analysis.questioning_improvement_tip}</span>
                        </div>
                    )}
                    <div className="mt-3 text-xs text-muted-foreground">
                        You asked {analysis.questions_asked_count} question{analysis.questions_asked_count !== 1 ? 's' : ''} • {analysis.questions_missed.length} key question{analysis.questions_missed.length !== 1 ? 's' : ''} missed
                    </div>
                </div>
            )}

            {/* Questions by Timing */}
            <div className="space-y-6">
                {(['Early', 'Mid', 'Late', 'Uncategorized'] as const).map(timing => {
                    const questions = questionsByTiming[timing]
                    if (questions.length === 0) return null

                    return (
                        <div key={timing}>
                            {timing !== 'Uncategorized' && (
                                <div className="flex items-center gap-2 mb-3">
                                    <Clock className="w-4 h-4 text-muted-foreground" />
                                    <h4 className="text-sm font-bold text-foreground uppercase tracking-wider">{timing} Conversation</h4>
                                </div>
                            )}
                            <div className="space-y-4">
                                {questions.map((q, idx) => (
                                    <div key={idx} className="p-5 rounded-xl bg-background border border-border hover:shadow-md transition-all group">
                                        {/* Question with badges */}
                                        <div className="flex flex-wrap items-start gap-2 mb-3">
                                            <span className="text-base font-semibold text-foreground italic flex-1 min-w-[200px]">"{q.question}"</span>
                                            {q.category && (
                                                <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider border ${getCategoryColor(q.category)}`}>
                                                    {q.category}
                                                </span>
                                            )}
                                            {q.timing && (
                                                <span className={`px-2 py-1 rounded text-xs font-semibold ${getTimingColor(q.timing)}`}>
                                                    {q.timing}
                                                </span>
                                            )}
                                        </div>

                                        {/* Details */}
                                        <div className="space-y-2 text-sm">
                                            <div className="flex gap-2">
                                                <span className="font-bold text-xs text-primary uppercase tracking-wider shrink-0">Why:</span>
                                                <span className="text-muted-foreground">{q.why_important}</span>
                                            </div>
                                            <div className="flex gap-2">
                                                <span className="font-bold text-xs text-emerald-600 uppercase tracking-wider shrink-0">When:</span>
                                                <span className="text-muted-foreground">{q.when_to_ask}</span>
                                            </div>
                                            <div className="flex gap-2">
                                                <span className="font-bold text-xs text-amber-600 uppercase tracking-wider shrink-0">Impact:</span>
                                                <span className="text-muted-foreground">{q.impact_if_asked}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )
                })}
            </div>
        </GlassCard>
    )
}

const ScorecardSection = ({ items }: { items: ScorecardItem[] }) => (
    <GlassCard>
        <SectionHeader icon={Target} title="Performance Scorecard" colorClass="text-emerald-500" bgClass="bg-emerald-500/10" />

        {/* Radar Chart Visualization */}
        <SkillRadarChart items={items} />

        <div className="space-y-8">
            {items?.map((item, i) => {
                const numScore = parseFloat(item.score.split('/')[0] || "0")
                const color = numScore >= 8 ? 'bg-emerald-500' : numScore >= 5 ? 'bg-amber-500' : 'bg-rose-500'

                return (
                    <div key={i} className="group border-b border-border/50 last:border-0 pb-8 last:pb-0">
                        {/* Header: Dimension + Score */}
                        <div className="flex justify-between items-end mb-3">
                            <h3 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors">{item.dimension}</h3>
                            <span className={`font-mono font-black text-2xl ${numScore >= 8 ? 'text-emerald-500' : numScore >= 5 ? 'text-amber-500' : 'text-rose-500'}`}>{item.score}</span>
                        </div>

                        <ProgressBar value={numScore * 10} colorClass={color} />

                        <div className="mt-5 space-y-4">
                            {/* PROOF / REASONING */}
                            <div className="bg-muted/30 rounded-xl p-4 border border-border/50">
                                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-2 block">Proof of Marks</span>
                                <p className="text-sm text-foreground leading-relaxed">
                                    {item.reasoning || item.description}
                                </p>
                                {item.quote && (
                                    <div className="mt-3 flex gap-2 text-sm text-muted-foreground/80 italic">
                                        <Quote className="w-4 h-4 shrink-0 opacity-50" />
                                        <span>"{item.quote}"</span>
                                    </div>
                                )}
                            </div>

                            {/* SUGGESTION */}
                            {item.suggestion && (
                                <div className="bg-emerald-500/5 rounded-xl p-4 border border-emerald-500/10 relative overflow-hidden">
                                    <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500/30" />
                                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest mb-2 block flex items-center gap-2">
                                        <Lightbulb className="w-3.5 h-3.5" /> Suggestion
                                    </span>
                                    <p className="text-sm font-medium text-foreground/90 leading-relaxed">
                                        {item.suggestion}
                                    </p>
                                </div>
                            )}

                            {/* ALTERNATIVE QUESTIONS */}
                            {item.alternative_questions && item.alternative_questions.length > 0 && (
                                <div className="mt-2">
                                    <p className="text-xs font-bold text-primary/70 uppercase tracking-wider mb-2">Try asking instead:</p>
                                    <div className="grid sm:grid-cols-2 gap-3">
                                        {item.alternative_questions.map((aq, idx) => (
                                            <div key={idx} className="p-3 bg-background rounded-lg border border-border text-xs shadow-sm">
                                                <span className="font-semibold text-primary block mb-1">"{aq.question}"</span>
                                                <span className="text-muted-foreground text-[10px] uppercase tracking-wide opacity-80">{aq.rationale}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )
            })}
        </div>
    </GlassCard>
)

// --- VIEW COMPONENTS ---




const SimulationView = ({ data }: { data: SimulationReportData }) => (
    <div className="space-y-8">
        {/* SECTION 1: Executive Summary */}
        {data.executive_summary && (
            <div className="grid lg:grid-cols-3 gap-6">
                <GlassCard className="lg:col-span-2 border-l-4 border-l-primary flex flex-col justify-center">
                    <SectionHeader icon={Activity} title="Executive Dashboard" colorClass="text-primary" bgClass="bg-primary/10" />
                    <p className="text-xl font-medium text-foreground/90 leading-relaxed mb-6">
                        {data.executive_summary.snapshot}
                    </p>
                    <div className="bg-primary/5 rounded-xl p-4 border border-primary/10">
                        <span className="text-xs font-bold text-primary uppercase tracking-widest block mb-2">Outcome Summary</span>
                        <p className="text-sm text-foreground/80">{data.executive_summary.outcome_summary}</p>
                    </div>
                </GlassCard>
                <GlassCard className="flex flex-col items-center justify-center text-center bg-gradient-to-b from-primary/10 to-transparent">
                    <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3">Final Score</span>
                    <div className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br from-blue-400 to-indigo-500">
                        {data.executive_summary.final_score || data.meta.overall_grade}
                    </div>
                </GlassCard>
            </div>
        )}

        {/* NEW: COACHING STYLE PROFILE */}
        {data.coaching_style && (
            <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/5 rounded-3xl p-1 shadow-sm">
                <GlassCard className="border-none shadow-none m-0 bg-background/60 backdrop-blur-sm">
                    <SectionHeader icon={Award} title="Coaching Style Profile" colorClass="text-emerald-500" bgClass="bg-emerald-500/10" />
                    <div className="flex flex-col md:flex-row gap-6 items-center">
                        <div className="bg-background rounded-2xl p-6 border border-emerald-500/20 text-center md:w-1/3 shrink-0 shadow-sm">
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Primary Style</span>
                            <div className="text-2xl lg:text-3xl font-black text-emerald-500 uppercase tracking-wide">{data.coaching_style.primary_style}</div>
                        </div>
                        <p className="text-lg lg:text-xl text-foreground/90 leading-relaxed font-medium italic">"{data.coaching_style.description}"</p>
                    </div>
                </GlassCard>
            </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
            {/* SECTION 2: Goal Attainment */}
            {data.goal_attainment && (
                <GlassCard>
                    <SectionHeader icon={Target} title="Goal Attainment" colorClass="text-blue-500" bgClass="bg-blue-500/10" />
                    <div className="flex items-center justify-between mb-6 pb-6 border-b border-border/50">
                        <span className="text-lg font-bold text-foreground">Attainment Score</span>
                        <span className="text-4xl font-black text-blue-500">{data.goal_attainment.score}</span>
                    </div>
                    <div className="space-y-6">
                        <div>
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Expectation vs Reality</span>
                            <p className="text-sm text-foreground/90 leading-relaxed">{data.goal_attainment.expectation_vs_reality}</p>
                        </div>
                        {data.goal_attainment.primary_gaps && data.goal_attainment.primary_gaps.length > 0 && (
                            <div>
                                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Primary Gaps</span>
                                <ul className="space-y-2">
                                    {data.goal_attainment.primary_gaps.map((gap, i) => (
                                        <li key={i} className="flex gap-2 text-sm text-foreground/80">
                                            <X className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" /> {gap}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {data.goal_attainment.observation_focus && data.goal_attainment.observation_focus.length > 0 && (
                            <div>
                                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Observation Focus</span>
                                <div className="flex flex-wrap gap-2">
                                    {data.goal_attainment.observation_focus.map((focus, i) => (
                                        <span key={i} className="px-2 py-1 bg-slate-500/10 text-slate-600 rounded text-xs font-medium border border-slate-500/20">{focus}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </GlassCard>
            )}

            {/* NEW: Context and Questioning Analysis */}
            {data.meta.scenario && <ScenarioContextSection scenario={data.meta.scenario} />}
            {data.question_analysis && <QuestionsSection analysis={data.question_analysis} />}
            {data.detailed_analysis && <DetailedAnalysisSection items={data.detailed_analysis} />}

            {/* SCORECARD AND HEAT MAP */}
            <div className="flex flex-col gap-8">
                {data.heat_map && data.heat_map.length > 0 && (
                    <GlassCard>
                        <SectionHeader icon={Activity} title="Competency Heat Map & Spider Graph" colorClass="text-purple-500" bgClass="bg-purple-500/10" />
                        <div className="grid lg:grid-cols-2 gap-8 items-center">
                            <CompetencyHeatMap items={data.heat_map} />
                            <div className="bg-muted/10 rounded-3xl p-4 border border-border/50">
                                <SkillRadarChart items={data.heat_map} />
                            </div>
                        </div>
                    </GlassCard>
                )}
                {data.scorecard && (
                    <ScorecardSection items={data.scorecard} />
                )}
            </div>
        </div>

        {/* DEEP DIVE ANALYSIS */}
        {data.deep_dive_analysis && data.deep_dive_analysis.length > 0 && (
            <GlassCard>
                <SectionHeader icon={BookOpen} title="Deep Dive Analysis" colorClass="text-indigo-500" bgClass="bg-indigo-500/10" />
                <div className="grid xl:grid-cols-2 gap-6">
                    {data.deep_dive_analysis.map((item, i) => (
                        <div key={i} className="bg-background rounded-xl p-5 border border-border shadow-sm">
                            <h3 className="font-bold text-lg text-indigo-600 mb-4 pb-2 border-b border-indigo-500/10">{item.topic}</h3>
                            <div className="space-y-3">
                                {item.tone && <div className="text-sm"><span className="font-bold text-muted-foreground">Tone:</span> <span className="text-foreground/90">{item.tone}</span></div>}
                                {item.language_impact && <div className="text-sm"><span className="font-bold text-muted-foreground">Language Impact:</span> <span className="text-foreground/90">{item.language_impact}</span></div>}
                                {item.comfort_level && <div className="text-sm"><span className="font-bold text-muted-foreground">Comfort Level:</span> <span className="text-foreground/90">{item.comfort_level}</span></div>}
                                {item.impact && <div className="text-sm"><span className="font-bold text-muted-foreground">Impact:</span> <span className="text-foreground/90">{item.impact}</span></div>}
                                {item.questions_asked && <div className="text-sm"><span className="font-bold text-muted-foreground">Questions:</span> <span className="text-foreground/90">{item.questions_asked}</span></div>}
                                {item.exploration && <div className="text-sm"><span className="font-bold text-muted-foreground">Exploration:</span> <span className="text-foreground/90">{item.exploration}</span></div>}
                                {item.understanding_depth && <div className="text-sm"><span className="font-bold text-muted-foreground">Understanding Depth:</span> <span className="text-foreground/90">{item.understanding_depth}</span></div>}
                                {item.analysis && <div className="text-sm text-foreground/90">{item.analysis}</div>}
                            </div>
                        </div>
                    ))}
                </div>
            </GlassCard>
        )}

        {/* BEHAVIOURAL & EQ */}
        {data.pattern_summary && (
            <GlassCard className="border-l-4 border-l-blue-500 shadow-md">
                <SectionHeader icon={Brain} title="Behavioural Pattern Summary" colorClass="text-blue-500" bgClass="bg-blue-500/10" />
                <p className="text-xl font-medium leading-relaxed text-foreground/90">{data.pattern_summary}</p>
            </GlassCard>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
            <div className="space-y-8 flex flex-col">
                {data.eq_analysis && <EQAnalysisSection items={data.eq_analysis} />}
                {data.turning_points && data.turning_points.length > 0 && (
                    <GlassCard>
                        <SectionHeader icon={History} title="Turning Points Detected" colorClass="text-amber-500" bgClass="bg-amber-500/10" />
                        <div className="space-y-4">
                            {data.turning_points.map((tp, i) => (
                                <div key={i} className="flex flex-col gap-2 p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 shadow-sm">
                                    <span className="text-xs font-bold text-amber-600 uppercase tracking-widest">{tp.timestamp}</span>
                                    <p className="text-sm text-foreground/90 leading-relaxed font-medium">{tp.point}</p>
                                </div>
                            ))}
                        </div>
                    </GlassCard>
                )}
            </div>
            <div className="space-y-8 flex flex-col">
                {data.behaviour_analysis && <BehaviourAnalysisSection items={data.behaviour_analysis} />}
            </div>
        </div>

        {/* STRENGTHS & MISSED OPPORTUNITIES */}
        <div className="grid lg:grid-cols-3 md:grid-cols-2 gap-6">
            {(data.strengths_and_improvements?.strengths || []).length > 0 && (
                <GlassCard>
                    <SectionHeader icon={CheckCircle2} title="Key Strengths" colorClass="text-emerald-500" bgClass="bg-emerald-500/10" />
                    <ul className="space-y-3">
                        {(data.strengths_and_improvements?.strengths || []).map((s, i) => (
                            <li key={i} className="flex gap-3 text-sm text-foreground/90 bg-emerald-500/5 p-3 rounded-lg border border-emerald-500/10">
                                <Check className="w-4 h-4 text-emerald-500 mt-0.5" /> {s}
                            </li>
                        ))}
                    </ul>
                </GlassCard>
            )}

            {((data.strengths_and_improvements?.missed_opportunities || []).length > 0 || (data.missed_opportunities || []).length > 0) && (
                <GlassCard>
                    <SectionHeader icon={AlertTriangle} title="Missed Opportunities" colorClass="text-amber-500" bgClass="bg-amber-500/10" />
                    <ul className="space-y-3">
                        {(data.strengths_and_improvements?.missed_opportunities || data.missed_opportunities || []).map((s, i) => (
                            <li key={i} className="flex gap-3 text-sm text-foreground/90 bg-amber-500/5 p-3 rounded-lg border border-amber-500/10">
                                <X className="w-4 h-4 text-amber-500 mt-0.5" /> {s}
                            </li>
                        ))}
                    </ul>
                </GlassCard>
            )}

            {data.ideal_questions && data.ideal_questions.length > 0 && (
                <GlassCard className="lg:col-span-1 md:col-span-2">
                    <SectionHeader icon={MessageSquare} title="Ideal Coaching Questions" colorClass="text-indigo-500" bgClass="bg-indigo-500/10" />
                    <ul className="space-y-4">
                        {data.ideal_questions.map((q, i) => (
                            <li key={i} className="text-sm font-medium text-foreground/80 italic pl-4 border-l-2 border-indigo-500/40">"{q}"</li>
                        ))}
                    </ul>
                </GlassCard>
            )}
        </div>

        {/* ACTION PLAN & FOLLOW UP */}
        <div className="grid lg:grid-cols-2 gap-6">
            {data.action_plan && (
                <GlassCard className="border-t-4 border-t-purple-500">
                    <SectionHeader icon={Activity} title="Action Plan" colorClass="text-purple-500" bgClass="bg-purple-500/10" />
                    <div className="space-y-4 mb-6 text-sm">
                        <div className="flex justify-between bg-purple-500/5 p-3 rounded-lg border border-purple-500/10">
                            <span className="font-bold text-purple-600">Owner</span>
                            <span className="font-medium">{data.action_plan.owner}</span>
                        </div>
                        <div className="flex justify-between bg-purple-500/5 p-3 rounded-lg border border-purple-500/10">
                            <span className="font-bold text-purple-600">Timeline</span>
                            <span className="font-medium">{data.action_plan.timeline}</span>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Specific Actions</span>
                            <ul className="space-y-2">
                                {data.action_plan.specific_actions?.map((action, i) => (
                                    <li key={i} className="flex gap-3 text-sm text-foreground/90">
                                        <div className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-600 flex items-center justify-center text-xs shrink-0 mt-0.5 font-bold">{i + 1}</div>
                                        {action}
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {data.action_plan.success_indicators && data.action_plan.success_indicators.length > 0 && (
                            <div className="pt-4 border-t border-border/50">
                                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Success Indicators</span>
                                <ul className="space-y-2 text-sm text-foreground/80">
                                    {data.action_plan.success_indicators.map((ind, i) => (
                                        <li key={i} className="flex gap-2 items-center"><Check className="w-4 h-4 text-emerald-500" /> {ind}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </GlassCard>
            )}

            {data.follow_up_strategy && (
                <GlassCard className="border-t-4 border-t-blue-500">
                    <SectionHeader icon={TrendingUp} title="Follow-Up Strategy" colorClass="text-blue-500" bgClass="bg-blue-500/10" />
                    <div className="space-y-6">
                        <div className="bg-blue-500/5 p-4 rounded-xl border border-blue-500/10">
                            <span className="text-xs font-bold text-blue-600 uppercase tracking-widest block mb-1">Review Cadence</span>
                            <p className="font-medium text-foreground">{data.follow_up_strategy.review_cadence}</p>
                        </div>

                        {data.follow_up_strategy.metrics_to_track && data.follow_up_strategy.metrics_to_track.length > 0 && (
                            <div>
                                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-2">Metrics to Track</span>
                                <div className="flex flex-col gap-2">
                                    {data.follow_up_strategy.metrics_to_track.map((metric, i) => (
                                        <div key={i} className="p-3 bg-background rounded-lg border border-border text-sm flex items-center gap-3 shadow-sm">
                                            <BarChart className="w-4 h-4 text-blue-500 shrink-0" /> <span className="font-medium text-foreground/90">{metric}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-border shadow-sm">
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest block mb-1">Accountability Method</span>
                            <p className="text-sm text-foreground/90 font-medium leading-relaxed">{data.follow_up_strategy.accountability_method}</p>
                        </div>
                    </div>
                </GlassCard>
            )}
        </div>

        {/* FINAL EVALUATION */}
        {data.final_evaluation && (
            <div className="bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-transparent p-1 rounded-3xl mt-4">
                <div className="bg-card rounded-[22px] p-6 lg:p-8 border border-indigo-500/20 shadow-sm">
                    <div className="flex flex-col md:flex-row gap-6 lg:gap-8 justify-between items-start mb-8 pb-8 border-b border-border/50">
                        <div>
                            <div className="flex items-center gap-3 mb-4">
                                <Flag className="w-8 h-8 text-indigo-500" />
                                <h2 className="text-2xl font-black text-foreground uppercase tracking-wide">Final Evaluation</h2>
                            </div>
                            <p className="text-muted-foreground max-w-2xl text-lg">Readiness assessment and long-term development pathway.</p>
                        </div>
                        <div className="flex gap-4 self-stretch md:self-auto">
                            {data.final_evaluation.maturity_rating && (
                                <div className="bg-indigo-500/10 px-6 py-4 rounded-2xl border border-indigo-500/20 text-center flex-1">
                                    <span className="text-xs font-bold text-indigo-600 uppercase tracking-widest block mb-1 whitespace-nowrap">Maturity Rating</span>
                                    <span className="text-3xl font-black text-indigo-500">{data.final_evaluation.maturity_rating}</span>
                                </div>
                            )}
                            {data.final_evaluation.readiness_level && (
                                <div className="bg-purple-500/10 px-6 py-4 rounded-2xl border border-purple-500/20 text-center flex-1">
                                    <span className="text-xs font-bold text-purple-600 uppercase tracking-widest block mb-1 whitespace-nowrap">Readiness</span>
                                    <span className="text-2xl lg:text-3xl font-black text-purple-500">{data.final_evaluation.readiness_level}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-8">
                        {data.final_evaluation.immediate_focus && data.final_evaluation.immediate_focus.length > 0 && (
                            <div>
                                <span className="text-sm font-bold text-foreground uppercase tracking-widest block mb-4 flex items-center gap-2">
                                    <Target className="w-4 h-4 text-primary" /> Immediate Focus Areas
                                </span>
                                <ul className="space-y-3">
                                    {data.final_evaluation.immediate_focus.map((focus, i) => (
                                        <li key={i} className="flex gap-3 p-3 bg-background border border-border rounded-xl text-sm font-medium shadow-sm">
                                            <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" /> <span className="text-foreground/90">{focus}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {data.final_evaluation.long_term_suggestion && (
                            <div className="bg-primary/5 p-6 rounded-2xl border border-primary/10 flex flex-col justify-center">
                                <span className="text-sm font-bold text-primary uppercase tracking-widest block mb-3 flex items-center gap-2">
                                    <TrendingUp className="w-4 h-4 text-primary" /> Long-Term Suggestion
                                </span>
                                <p className="text-foreground/90 leading-relaxed italic text-base lg:text-lg font-medium">{data.final_evaluation.long_term_suggestion}</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        )}
    </div>
)
