"use client"

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { motion } from "framer-motion"
import {
    Sparkles,
    Swords,
    UserCog,
    DollarSign, Users, ShoppingCart, GraduationCap, AlertTriangle, Check, ChevronDown, ChevronUp, Info,
    Type, User, MessageSquare, BrainCircuit, Loader2
} from "lucide-react"
import Navigation from "../components/landing/Navigation"
import { getApiUrl } from "../lib/api"

const ICON_MAP: any = {
    Users, ShoppingCart, GraduationCap, AlertTriangle, DollarSign, UserCog
}

const DEFAULT_SCENARIOS = [
    {
        name: "Coaching Simulations",
        color: "from-amber-500 to-orange-600",
        scenarios: [
            {
                title: "Good Attitude, Poor Results",
                description: "Coach a sincere employee who keeps missing targets. Improve performance without demotivating the employee.",
                ai_role: "Sales Associate",
                user_role: "Store Manager",
                scenario: "CONTEXT: The employee is sincere and well-liked, but their results have been consistently below target for the last 3 months. You need to coach them to understand the gap, identify root causes, and agree on a clear improvement plan.\n\nYOUR OBJECTIVES:\n1. Create a safe, respectful tone\n2. Use facts to discuss the performance gap\n3. Explore reasons behind the gap\n4. Agree on 2-3 actions and a follow-up plan",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-01-PERF-001"
            },
            {
                title: "High Performer, Toxic Attitude",
                description: "Address behavior issues with a top performer without losing performance momentum.",
                ai_role: "Top Sales Performer",
                user_role: "Team Leader",
                scenario: "CONTEXT: The employee is a top performer whose sales numbers consistently exceed target. However, multiple team members report they are sarcastic, dismissive, and undermine colleagues in front of customers. You must address the behavior without losing performance momentum.\n\nYOUR OBJECTIVES:\n1. Maintain psychological safety\n2. Address behavior clearly using examples\n3. Separate performance from behavior\n4. Create ownership and behavior shift commitment",
                icon: "AlertTriangle",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-02-BEH-001"
            },
            {
                title: "The Silent Disengagement",
                description: "Re-engage a once-dependable team member who has shown a decline in initiative.",
                ai_role: "Disengaged Team Member",
                user_role: "Manager",
                scenario: "CONTEXT: The team member was once dependable, but over the last 6-8 weeks, their energy has dropped. They complete tasks but show no initiative and avoid extra responsibilities. There are no performance complaints—just a decline in engagement.\n\nYOUR OBJECTIVES:\n1. Create psychological safety\n2. Explore underlying causes without assumptions\n3. Avoid an accusatory tone\n4. Help the team member reconnect to purpose or ownership",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-03-MOT-001"
            },
            {
                title: "Pushing Back Upwards",
                description: "Communicate concerns about unrealistic targets to a Regional Director professionally.",
                ai_role: "Regional Director",
                user_role: "Sales Manager",
                scenario: "CONTEXT: Your Regional Director set a new quarterly sales target 35% higher than last quarter, which you believe is unrealistic due to staffing, market, and inventory constraints. You need to communicate concerns without appearing resistant or negative.\n\nYOUR OBJECTIVES:\n1. Remain professional and composed\n2. Use data to support your position\n3. Avoid an emotional or defensive tone\n4. Offer alternative solutions",
                icon: "UserCog",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-04-COM-001"
            },
            {
                title: "Two Team Members, One Growing Conflict",
                description: "Resolve visible tension and breakdown in communication between two team members.",
                ai_role: "Conflicted Team Members",
                user_role: "Team Manager",
                scenario: "CONTEXT: Two team members' communication has broken down; each claims the other is causing delays and mistakes. Tension is now visible to other team members, and you have called both into a joint meeting to resolve it.\n\nYOUR OBJECTIVES:\n1. Establish neutrality\n2. Prevent blame escalation\n3. Identify the root cause\n4. Create a practical working agreement",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-05-CON-001"
            },
            {
                title: "The Escalating Client",
                description: "Manage a frustrated key client threatening to escalate a delivery issue.",
                ai_role: "Frustrated Key Client",
                user_role: "Account Manager",
                scenario: "CONTEXT: A key client is frustrated over a delivery issue and believes your team failed to meet expectations. They are threatening to escalate to senior leadership and reconsider future business.\n\nYOUR OBJECTIVES:\n1. Stay composed under pressure\n2. Acknowledge concerns without over-admitting liability\n3. Clarify facts\n4. Offer a structured path forward",
                icon: "ShoppingCart",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-06-CUST-001"
            },
            {
                title: "The Overloaded Manager",
                description: "Address a pattern of poor ownership with a capable team member.",
                ai_role: "Team Member",
                user_role: "Manager",
                scenario: "CONTEXT: You are overwhelmed as critical tasks often end up back on your desk because a capable team member rarely takes full ownership. You need to address this pattern and redistribute responsibility.\n\nYOUR OBJECTIVES:\n1. Clarify expectations\n2. Avoid blame\n3. Define ownership boundaries\n4. Establish an accountability structure",
                icon: "GraduationCap",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-07-LEAD-001"
            },
            {
                title: "Resistance to the New System",
                description: "Understand and manage subtle resistance to organizational change.",
                ai_role: "Experienced Team Member",
                user_role: "Team Lead",
                scenario: "CONTEXT: An experienced team member is subtly resisting a new organizational system, frequently calling it unnecessary. Their attitude is beginning to influence others.\n\nYOUR OBJECTIVES:\n1. Avoid confrontation\n2. Understand resistance drivers\n3. Reinforce the purpose of the change\n4. Encourage ownership in adaptation",
                icon: "AlertTriangle",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-08-CHG-001"
            },
            {
                title: "Why Didn't I Get Promoted?",
                description: "Provide developmental feedback to a high performer not selected for promotion.",
                ai_role: "High Performer",
                user_role: "Manager",
                scenario: "CONTEXT: A high performer applied for a promotion but was not selected. They have requested a meeting to understand why they were not chosen.\n\nYOUR OBJECTIVES:\n1. Acknowledge the emotional impact\n2. Provide specific developmental feedback\n3. Avoid vague generalizations\n4. Offer a forward-looking growth plan",
                icon: "GraduationCap",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-09-CAR-001"
            },
            {
                title: "Burnout Behind the Smile",
                description: "Sustainably explore signs of exhaustion and burnout with a high performer.",
                ai_role: "Exhausted Performer",
                user_role: "Manager",
                scenario: "CONTEXT: The employee remains high-performing, but you have noticed signs of exhaustion, such as shorter responses and avoiding extra tasks. You suspect early signs of burnout.\n\nYOUR OBJECTIVES:\n1. Observe without accusing\n2. Create psychological safety\n3. Explore wellbeing sensitively\n4. Protect sustainable performance",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "coaching_sim",
                session_mode: "skill_assessment",
                simulation_id: "SIM-10-WELL-001"
            }
        ]
    }
]

const MENTORSHIP_SCENARIOS = [
    {
        name: "Mentorship Simulations",
        color: "from-blue-500 to-indigo-600",
        scenarios: [
            {
                title: "Seeking Growth Amidst Struggle",
                description: "As a Sales Associate, navigate a performance review with your manager to find a path forward without losing your job.",
                ai_role: "Store Manager",
                user_role: "Sales Associate",
                scenario: "CONTEXT: You are a sincere and dedicated employee, but you've missed your targets for 3 months. You are meeting with your Manager. You need to be honest about your struggles while demonstrating your commitment to improve.\n\nYOUR OBJECTIVES:\n1. Openly acknowledge the performance gap\n2. Share specific hurdles you are facing\n3. Ask for specific coaching or resources\n4. Commit to a realistic improvement plan",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-01-PERF-001"
            },
            {
                title: "Managing Your Reputation",
                description: "As a Top Performer, learn to receive feedback about your 'toxic' attitude and pivot toward leadership behavior.",
                ai_role: "Team Leader",
                user_role: "Top Sales Performer",
                scenario: "CONTEXT: Your sales numbers are the best in the company, but your Team Leader has called a meeting to discuss your 'attitude.' You often feel frustrated by others' lack of pace, but you need to hear the feedback without becoming defensive.\n\nYOUR OBJECTIVES:\n1. Listen to feedback without interrupting\n2. Acknowledge the impact of your tone on others\n3. Seek advice on how to mentor instead of criticize\n4. Agree on behavior changes to protect team culture",
                icon: "AlertTriangle",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-02-BEH-001"
            },
            {
                title: "Breaking the Silence",
                description: "As a disengaged employee, communicate your lack of motivation to your manager to find a new sense of purpose.",
                ai_role: "Manager",
                user_role: "Disengaged Team Member",
                scenario: "CONTEXT: You've been coasting for two months. You're doing the bare minimum because you feel stuck. Your manager has noticed. Use this meeting to express why you've lost your spark and what would re-energize you.\n\nYOUR OBJECTIVES:\n1. Honestly express your current state of mind\n2. Identify what parts of the role no longer fulfill you\n3. Propose a new project or area of interest\n4. Collaborate on a plan to rebuild engagement",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-03-MOT-001"
            },
            {
                title: "Advocating for the Team",
                description: "As a Sales Manager, present a data-driven case to your Regional Director to adjust unrealistic targets.",
                ai_role: "Regional Director",
                user_role: "Sales Manager",
                scenario: "CONTEXT: You've been handed a 35% increase in targets that you know is impossible. You need to convince your Regional Director to reconsider by providing evidence, rather than just complaining.\n\nYOUR OBJECTIVES:\n1. Present market and inventory data clearly\n2. Stay professional despite potential pressure\n3. Propose a 'stretch but reachable' alternative\n4. Secure a commitment for more resources or adjusted goals",
                icon: "UserCog",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-04-COM-001"
            },
            {
                title: "Navigating Peer Conflict",
                description: "As one of the conflicted parties, work with your manager to resolve a breakdown in communication with a colleague.",
                ai_role: "Team Manager",
                user_role: "Conflicted Team Member",
                scenario: "CONTEXT: You and a colleague are at odds. You feel they are causing the delays, but you are now in a joint meeting with your Manager. You need to move past blame to find a professional solution.\n\nYOUR OBJECTIVES:\n1. State your perspective using 'I' statements\n2. Listen to your colleague's side with neutrality\n3. Identify the specific bottleneck in the workflow\n4. Agree to a new communication protocol",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-05-CON-001"
            },
            {
                title: "Recovering Client Trust",
                description: "As an Account Manager, handle a high-stakes meeting with a frustrated client to save the account.",
                ai_role: "Frustrated Key Client",
                user_role: "Account Manager",
                scenario: "CONTEXT: Your team missed a delivery. The client is furious and on the verge of leaving. You need to manage their emotions while protecting the company's reputation and providing a solution.\n\nYOUR OBJECTIVES:\n1. De-escalate the client's anger through active listening\n2. Avoid making promises you can't keep\n3. Outline a concrete recovery plan\n4. Secure a follow-up meeting to confirm resolution",
                icon: "ShoppingCart",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-06-CUST-001"
            },
            {
                title: "Stepping into Ownership",
                description: "As a Team Member, learn to stop escalating tasks and start taking full accountability for your projects.",
                ai_role: "Manager",
                user_role: "Team Member",
                scenario: "CONTEXT: You are capable, but you often hand tasks back to your manager when they get difficult. Your manager wants to talk about 'ownership.' You need to understand how to manage up and take the lead.\n\nYOUR OBJECTIVES:\n1. Acknowledge the pattern of shifting tasks back\n2. Identify why you hesitate to make final decisions\n3. Ask for clear decision-making boundaries\n4. Commit to a 'solution-first' reporting style",
                icon: "GraduationCap",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-07-LEAD-001"
            },
            {
                title: "Adapting to Change",
                description: "As an Experienced Team Member, discuss your concerns about a new system with your Lead to find a middle ground.",
                ai_role: "Team Lead",
                user_role: "Experienced Team Member",
                scenario: "CONTEXT: You think the new system is a waste of time. You've been vocal about it. Your Team Lead wants to discuss your resistance. Use this to voice valid concerns while showing you're a team player.\n\nYOUR OBJECTIVES:\n1. Share specific technical concerns about the new system\n2. Avoid sounding 'anti-change' for the sake of it\n3. Offer to help pilot a more efficient version\n4. Agree to support the transition for the sake of the team",
                icon: "AlertTriangle",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-08-CHG-001"
            },
            {
                title: "Processing the 'No'",
                description: "As a High Performer, professionally handle being passed over for a promotion and get a roadmap for the next one.",
                ai_role: "Manager",
                user_role: "High Performer",
                scenario: "CONTEXT: You didn't get the promotion you wanted. You are disappointed. You are meeting your manager to find out why and what you need to do to be the top candidate next time.\n\nYOUR OBJECTIVES:\n1. Manage your disappointment professionally\n2. Ask for specific, actionable skill gaps\n3. Request a mentor or training for those gaps\n4. Establish a 6-month review timeline for growth",
                icon: "GraduationCap",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-09-CAR-001"
            },
            {
                title: "Admitting Burnout",
                description: "As an Exhausted Performer, speak up about your mental health and workload before you hit a breaking point.",
                ai_role: "Manager",
                user_role: "Exhausted Performer",
                scenario: "CONTEXT: You are burned out. You're still hitting numbers, but you're exhausted and starting to resent the work. Your manager has noticed you're quieter. You need to ask for help without appearing weak.\n\nYOUR OBJECTIVES:\n1. Describe your current workload and stress levels\n2. Propose a temporary adjustment to responsibilities\n3. Discuss sustainable working habits\n4. Reaffirm your commitment to the long-term mission",
                icon: "Users",
                output_type: "scored_report",
                mode: "evaluation",
                scenario_type: "mentorship_sim",
                session_mode: "skill_assessment",
                simulation_id: "MENT-10-WELL-001"
            }
        ]
    }
]


export default function Practice() {
    const navigate = useNavigate()

    const [selectedCharacter, setSelectedCharacter] = useState<"alex" | "sarah">("alex")

    const [expandedScenario, setExpandedScenario] = useState<string | null>(null)
    const [isStartingSession, setIsStartingSession] = useState(false)
    const [startingScenarioTitle, setStartingScenarioTitle] = useState<string | null>(null)

    // Custom Scenario State
    const [customForm, setCustomForm] = useState({
        title: "",
        userRole: "",
        aiRole: "",
        context: "",
        mode: "practice" as "practice",
        sessionType: "assessment" as "assessment" | "mentorship"
    })

    const [globalMode, setGlobalMode] = useState<"assessment" | "mentorship">("assessment")


    // Helper function to parse scenario text
    const parseScenarioDetails = (scenarioText: string) => {
        const sections = {
            context: '',
            focusAreas: '',
            aiBehavior: ''
        }

        // Extract CONTEXT
        const contextMatch = scenarioText.match(/CONTEXT:\s*(.*?)(?=\n\n|FOCUS AREAS:|AI BEHAVIOR:|$)/s)
        if (contextMatch) sections.context = contextMatch[1].trim()

        // Extract FOCUS AREAS
        const focusMatch = scenarioText.match(/FOCUS AREAS:\s*(.*?)(?=\n\n|AI BEHAVIOR:|$)/s)
        if (focusMatch) sections.focusAreas = focusMatch[1].trim()

        // Extract AI BEHAVIOR
        const behaviorMatch = scenarioText.match(/AI BEHAVIOR:\s*(.*?)$/s)
        if (behaviorMatch) sections.aiBehavior = behaviorMatch[1].trim()

        return sections
    }



    const handleStartSession = async (data: {
        role: string
        ai_role: string
        scenario: string
        scenario_type?: string
        session_mode?: string
        ai_character?: string
        title?: string
        mode?: string
        simulation_id?: string
        flip_roles?: boolean
    }) => {
        if (isStartingSession) return

        try {
            setIsStartingSession(true)
            setStartingScenarioTitle(data.title || 'custom')
            // Call backend to create session
            const response = await fetch(getApiUrl('/api/session/start'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    role: data.role,
                    ai_role: data.ai_role,
                    scenario: data.scenario,
                    framework: 'auto',
                    scenario_type: data.scenario_type,
                    ai_character: data.ai_character || selectedCharacter,
                    title: data.title,
                    mode: data.mode,
                    simulation_id: data.simulation_id,
                    flip_roles: data.flip_roles || false
                })
            })

            if (!response.ok) {
                throw new Error('Failed to start session')
            }

            const result = await response.json()
            const session_id = result.session_id
            const summary = result.summary

            // Also save to localStorage for offline reference
            localStorage.setItem(
                `session_${session_id}`,
                JSON.stringify({
                    role: data.role,
                    ai_role: data.ai_role,
                    scenario: data.scenario,
                    createdAt: new Date().toISOString(),
                    transcript: [{ role: "assistant", content: summary }],
                    sessionId: session_id,
                    completed: false,
                    scenario_type: result.scenario_type || 'custom',
                    ai_character: result.ai_character || data.ai_character,
                    multi_characters: result.multi_characters || false,
                    characters: result.characters || null
                }),
            )

            navigate(`/conversation/${session_id}`)

        } catch (error) {
            console.error("Error starting session:", error)

            toast.error("Failed to start session", {
                description: "Please make sure the backend is running."
            })
            setIsStartingSession(false)
            setStartingScenarioTitle(null)
        }
    }

    return (
        <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30 relative overflow-x-hidden">
            <Navigation />

            {/* Ambient Background */}
            <div className="fixed inset-0 pointer-events-none -z-10">
                <div className="absolute top-[10%] right-[5%] w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] animate-pulse-glow" />
                <div className="absolute bottom-[10%] left-[5%] w-[500px] h-[500px] bg-purple-600/5 rounded-full blur-[100px] animate-pulse-glow" style={{ animationDelay: '2s' }} />
            </div>

            <main className="container mx-auto px-4 sm:px-6 pt-24 sm:pt-32 pb-16 sm:pb-32">
                {/* Hero Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="text-center mb-20 relative z-10"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-bold uppercase tracking-wider mb-6 animate-fade-in-up">
                        <Sparkles className="w-4 h-4" /> AI Training Arena
                    </div>
                    <h1 className="text-4xl sm:text-5xl md:text-7xl font-black mb-6 tracking-tight leading-none">
                        Practice Conversations <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-purple-500 to-pink-500 animate-gradient">
                            That Matter
                        </span>
                    </h1>
                    <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                        Select a partner, choose your mode, and master your skills.
                    </p>
                </motion.div>

                {/* Character Selection */}
                <div className="flex flex-col items-center mb-20 relative">
                    <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-border to-transparent -z-10" />
                    <div className="bg-background px-4 relative z-10 mb-8">
                        <span className="text-xs font-black text-primary tracking-[0.2em] uppercase border border-primary/50 bg-primary/10 px-3 py-1 rounded-full">Step 01</span>
                    </div>
                    <h3 className="text-2xl font-bold text-foreground mb-8 tracking-tight">Select Your Partner</h3>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 md:gap-8 w-full max-w-2xl px-4">
                        {[
                            {
                                id: "alex",
                                name: "Alex",
                                role: "Senior AI Coach",
                                desc: "Fully adaptive roleplay partner. Shifts dynamically between evaluation and mentorship.",
                                img: "/alex.png",
                                voice: "Male Voice (Fable)",
                                color: "blue",
                                traits: ["Scenario Adaptive", "Real-time Feedback", "Role Improvisation"]
                            },
                            {
                                id: "sarah",
                                name: "Sarah",
                                role: "Senior AI Coach",
                                desc: "Fully adaptive roleplay partner. Shifts dynamically between evaluation and mentorship.",
                                img: "/sarah.png",
                                voice: "Female Voice (Nova)",
                                color: "purple",
                                traits: ["Scenario Adaptive", "Real-time Feedback", "Role Improvisation"]
                            }
                        ].map((char) => (
                            <motion.button
                                key={char.id}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setSelectedCharacter(char.id as any)}
                                className={`relative group overflow-hidden rounded-3xl border-2 transition-all duration-300 text-left h-full flex flex-col ${selectedCharacter === char.id
                                    ? `border-${char.color}-500 bg-gradient-to-b from-${char.color}-900/40 to-card shadow-[0_0_40px_rgba(${char.color === 'blue' ? '59,130,246' : '168,85,247'},0.3)]`
                                    : "border-border bg-card/40 hover:bg-card/60 hover:border-primary/50"
                                    }`}
                            >
                                <div className="relative h-48 sm:h-64 overflow-hidden w-full">
                                    <div className={`absolute inset-0 bg-gradient-to-t from-card via-transparent to-transparent z-10`} />
                                    <img
                                        src={char.img}
                                        alt={char.name}
                                        className={`w-full h-full object-cover transition-transform duration-700 ${selectedCharacter === char.id ? 'scale-105' : 'group-hover:scale-110 opacity-60 group-hover:opacity-100'}`}
                                    />

                                    {/* Selection Check */}
                                    {selectedCharacter === char.id && (
                                        <div className="absolute top-4 right-4 z-20">
                                            <motion.div
                                                initial={{ scale: 0 }}
                                                animate={{ scale: 1 }}
                                                className={`w-10 h-10 rounded-full bg-${char.color}-500 flex items-center justify-center shadow-lg border-2 border-white/20`}
                                            >
                                                <Check className="w-6 h-6 text-white" />
                                            </motion.div>
                                        </div>
                                    )}
                                </div>

                                <div className="p-4 sm:p-6 relative z-20 -mt-16 sm:-mt-20 flex-1 flex flex-col">
                                    <div className="mb-auto">
                                        <h4 className={`text-2xl sm:text-3xl font-black mb-1 ${selectedCharacter === char.id ? "text-foreground" : "text-muted-foreground"}`}>{char.name}</h4>
                                        <p className={`text-xs font-bold uppercase tracking-widest mb-4 ${selectedCharacter === char.id ? `text-${char.color}-400` : "text-muted-foreground"}`}>{char.role}</p>

                                        <p className="text-sm text-muted-foreground leading-relaxed">
                                            {char.desc}
                                        </p>
                                    </div>
                                </div>
                            </motion.button>
                        ))}
                    </div>
                </div>




                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="max-w-6xl mx-auto"
                >
                    <div className="space-y-12">
                        {/* Mode Toggle for Guided */}

                        {/* Step 2 Header */}
                        <div className="flex flex-col items-center mb-8 relative">
                            <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-border to-transparent -z-10" />
                            <div className="bg-background px-4 relative z-10 mb-8">
                                <span className="text-xs font-black text-indigo-500 tracking-[0.2em] uppercase border border-indigo-900/50 bg-indigo-900/20 px-3 py-1 rounded-full">Step 02</span>
                            </div>
                            <h3 className="text-2xl font-bold text-foreground tracking-tight mb-6">Choose Your Challenge</h3>

                            {/* Global Mode Toggle */}
                            <div className="flex bg-card/60 border border-border/50 rounded-full p-1.5 shadow-xl backdrop-blur-md mb-8">
                                <button
                                    onClick={() => setGlobalMode("assessment")}
                                    className={`relative px-8 py-3 rounded-full text-sm font-bold transition-all duration-300 ${globalMode === "assessment"
                                        ? "text-primary bg-primary/10 shadow-[0_2px_10px_rgba(59,130,246,0.15)]"
                                        : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                        }`}
                                >
                                    Assessment
                                </button>
                                <button
                                    onClick={() => setGlobalMode("mentorship")}
                                    className={`relative px-8 py-3 rounded-full text-sm font-bold transition-all duration-300 ${globalMode === "mentorship"
                                        ? "text-emerald-500 bg-emerald-500/10 shadow-[0_2px_10px_rgba(16,185,129,0.15)]"
                                        : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                        }`}
                                >
                                    Mentorship
                                </button>
                            </div>
                        </div>

                        {(globalMode === "assessment" ? DEFAULT_SCENARIOS : MENTORSHIP_SCENARIOS).map((category, idx) => (
                            <div key={idx} className="space-y-6">
                                <div className="flex items-center gap-4">
                                    <div className={`h-8 w-1 bg-gradient-to-b ${category.color} rounded-full`} />
                                    <h3 className="text-2xl font-bold text-foreground tracking-tight">{category.name}</h3>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                                    {category.scenarios.map((scenario: any, sIdx: number) => {
                                        const Icon = ICON_MAP[scenario.icon] || Sparkles
                                        // Use scenario_type for badge display
                                        const scenarioType = scenario.scenario_type || 'custom'
                                        const typeLabels: any = {
                                            'coaching': 'Coaching',
                                            'negotiation': 'Negotiation',
                                            'reflection': 'Reflection',
                                            'mentorship': 'Mentorship',
                                            'coaching_sim': 'Simulation',
                                            'custom': 'Custom'
                                        }
                                        const typeColors: any = {
                                            'coaching': 'bg-blue-500/10 text-slate-900 dark:text-blue-300 border-blue-500/30',
                                            'negotiation': 'bg-green-500/10 text-slate-900 dark:text-green-300 border-green-500/30',
                                            'reflection': 'bg-purple-500/10 text-slate-900 dark:text-purple-300 border-purple-500/30',
                                            'mentorship': 'bg-emerald-500/10 text-slate-900 dark:text-emerald-300 border-emerald-500/30',
                                            'coaching_sim': 'bg-amber-500/10 text-slate-900 dark:text-amber-300 border-amber-500/30',
                                            'custom': 'bg-amber-500/10 text-slate-900 dark:text-amber-300 border-amber-500/20'
                                        }
                                        const typeIcons: any = {
                                            'coaching': Users,
                                            'negotiation': ShoppingCart,
                                            'reflection': GraduationCap,
                                            'mentorship': UserCog,
                                            'coaching_sim': Swords,
                                            'custom': Sparkles
                                        }
                                        const modeLabel = typeLabels[scenarioType] || 'Custom'
                                        const ModeIcon = typeIcons[scenarioType] || Sparkles
                                        const badgeColor = typeColors[scenarioType] || typeColors['custom']

                                        // Dynamic Role Handling
                                        let displayAiRole = scenario.ai_role
                                        let displayDescription = scenario.description

                                        // Update text for Learning scenario (Coach Alex/Sarah) or "AI Coach"
                                        if (scenario.scenario_type === 'reflection' || displayAiRole.includes('Coach Alex') || displayAiRole === 'AI Coach') {
                                            const charName = selectedCharacter === 'sarah' ? 'Sarah' : 'Alex'
                                            displayAiRole = `Coach ${charName}`
                                            displayDescription = displayDescription.replace(/Coach Alex/g, `Coach ${charName}`).replace(/AI Coach/g, `Coach ${charName}`)
                                        }

                                        return (
                                            <div
                                                key={sIdx}
                                                onClick={() => handleStartSession({
                                                    role: scenario.user_role,
                                                    ai_role: displayAiRole,
                                                    scenario: scenario.scenario,
                                                    scenario_type: scenario.scenario_type,
                                                    session_mode: scenario.session_mode,
                                                    ai_character: selectedCharacter,
                                                    title: scenario.title,
                                                    mode: scenario.mode,
                                                    simulation_id: scenario.simulation_id,
                                                    // Flip roles flag for mentorship scenarios so backend can swap if needed
                                                    flip_roles: scenario.scenario_type === 'mentorship'
                                                })}
                                                className={`group relative p-6 bg-card/40 hover:bg-card/60 border border-border/50 hover:border-primary/30 rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden ${isStartingSession ? 'opacity-70 pointer-events-none' : ''}`}
                                            >
                                                {isStartingSession && startingScenarioTitle === scenario.title && (
                                                    <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
                                                        <Loader2 className="w-8 h-8 text-primary animate-spin mb-2" />
                                                        <span className="text-sm font-bold text-primary">Starting...</span>
                                                    </div>
                                                )}
                                                <div className={`absolute top-0 right-0 p-16 rounded-full blur-2xl opacity-0 group-hover:opacity-10 bg-gradient-to-br ${category.color} transition-opacity duration-500`} />

                                                <div className="relative z-10">
                                                    <div className="flex justify-between items-start mb-4">
                                                        <div className={`w-12 h-12 rounded-xl bg-muted/50 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 text-muted-foreground group-hover:text-foreground`}>
                                                            <Icon className="w-6 h-6" />
                                                        </div>
                                                        <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${badgeColor} flex items-center gap-1.5`}>
                                                            <ModeIcon className="w-3 h-3" />
                                                            {modeLabel}
                                                        </div>
                                                    </div>

                                                    <h4 className="text-lg font-bold text-foreground mb-4 group-hover:text-primary transition-colors">{scenario.title}</h4>

                                                    <div className="flex flex-col gap-2 mb-4">
                                                        <div className="flex items-center gap-2 text-xs">
                                                            <span className="font-bold text-muted-foreground uppercase">Your Role:</span>
                                                            <span className="text-foreground font-medium">{scenario.user_role}</span>
                                                        </div>
                                                        <div className="flex items-center gap-2 text-xs">
                                                            <span className="font-bold text-muted-foreground uppercase">Partner:</span>
                                                            <span className="text-primary font-medium">{displayAiRole}</span>
                                                        </div>
                                                    </div>

                                                    {/* Expandable Scenario Details */}
                                                    <div className="mb-4">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                setExpandedScenario(
                                                                    expandedScenario === scenario.title ? null : scenario.title
                                                                )
                                                            }}
                                                            className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary hover:text-primary/80 transition-colors"
                                                        >
                                                            <Info className="w-3.5 h-3.5" />
                                                            <span>Scenario Details</span>
                                                            {expandedScenario === scenario.title ? (
                                                                <ChevronUp className="w-3.5 h-3.5" />
                                                            ) : (
                                                                <ChevronDown className="w-3.5 h-3.5" />
                                                            )}
                                                        </button>

                                                        {expandedScenario === scenario.title && (
                                                            <motion.div
                                                                initial={{ opacity: 0, height: 0 }}
                                                                animate={{ opacity: 1, height: "auto" }}
                                                                exit={{ opacity: 0, height: 0 }}
                                                                transition={{ duration: 0.3 }}
                                                                className="mt-3 p-4 bg-muted/30 rounded-xl border border-border/50 text-xs"
                                                                onClick={(e) => e.stopPropagation()}
                                                            >
                                                                {(() => {
                                                                    const details = parseScenarioDetails(scenario.scenario)
                                                                    return (
                                                                        <div className="text-muted-foreground leading-relaxed">
                                                                            {details.context}
                                                                        </div>
                                                                    )
                                                                })()}
                                                            </motion.div>
                                                        )}
                                                    </div>

                                                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground group-hover:text-primary transition-colors mt-4">
                                                        <span>Start Scenario</span>
                                                        <Swords className="w-3 h-3" />
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        ))}

                        {/* Custom Scenario Builder */}
                        <div className="relative mt-24">
                            <div className="flex flex-col items-center mb-10 relative">
                                <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-border to-transparent -z-10" />
                                <div className="bg-background px-6 relative z-10 mb-6">
                                    <span className="text-xs font-black text-amber-500 tracking-[0.2em] uppercase border border-amber-500/30 bg-amber-500/10 px-4 py-1.5 rounded-full shadow-[0_0_15px_rgba(245,158,11,0.2)]">Create Your Own</span>
                                </div>
                                <h3 className="text-3xl sm:text-4xl font-black text-foreground tracking-tight mb-2">Build a Scenario</h3>
                                <p className="text-muted-foreground text-center max-w-lg mb-8">Design a specific situation to test your skills or explore a new dynamic.</p>

                                {/* Custom Mode Toggle */}
                                <div className="flex bg-card/60 border border-border/50 rounded-full p-1.5 shadow-xl backdrop-blur-md">
                                    <button
                                        onClick={() => setCustomForm({ ...customForm, sessionType: "assessment" })}
                                        className={`relative px-8 py-3 rounded-full text-sm font-bold transition-all duration-300 ${customForm.sessionType === "assessment"
                                            ? "text-primary bg-primary/10 shadow-[0_2px_10px_rgba(59,130,246,0.15)]"
                                            : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                            }`}
                                    >
                                        Assessment
                                    </button>
                                    <button
                                        onClick={() => setCustomForm({ ...customForm, sessionType: "mentorship" })}
                                        className={`relative px-8 py-3 rounded-full text-sm font-bold transition-all duration-300 ${customForm.sessionType === "mentorship"
                                            ? "text-emerald-500 bg-emerald-500/10 shadow-[0_2px_10px_rgba(16,185,129,0.15)]"
                                            : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                            }`}
                                    >
                                        Mentorship
                                    </button>
                                </div>
                            </div>

                            <div className="bg-card/40 border border-white/10 rounded-3xl p-6 sm:p-10 backdrop-blur-md shadow-2xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[100px] pointer-events-none" />

                                <div className="space-y-8 relative z-10">

                                    {/* 1. Basics */}
                                    <div className="space-y-6">
                                        <div className="grid grid-cols-1 gap-6">
                                            <div className="space-y-2">
                                                <label className="text-xs font-bold uppercase text-muted-foreground ml-1">Scenario Title</label>
                                                <div className="relative group">
                                                    <div className="absolute left-3 top-3 text-muted-foreground group-focus-within:text-primary transition-colors">
                                                        <Type className="w-5 h-5" />
                                                    </div>
                                                    <input
                                                        type="text"
                                                        value={customForm.title}
                                                        onChange={(e) => setCustomForm({ ...customForm, title: e.target.value })}
                                                        placeholder="e.g., Managing Underperformance"
                                                        className="w-full bg-background/50 border border-border group-hover:border-primary/30 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                            <div className="space-y-2">
                                                <label className="text-xs font-bold uppercase text-muted-foreground ml-1">Your Role</label>
                                                <div className="relative group">
                                                    <div className="absolute left-3 top-3 text-muted-foreground group-focus-within:text-indigo-400 transition-colors">
                                                        <User className="w-5 h-5" />
                                                    </div>
                                                    <input
                                                        type="text"
                                                        value={customForm.userRole}
                                                        onChange={(e) => setCustomForm({ ...customForm, userRole: e.target.value })}
                                                        placeholder="e.g., Engineering Lead"
                                                        className="w-full bg-background/50 border border-border group-hover:border-indigo-500/30 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all font-medium"
                                                    />
                                                </div>
                                            </div>
                                            <div className="space-y-2">
                                                <label className="text-xs font-bold uppercase text-muted-foreground ml-1">Partner Role (AI)</label>
                                                <div className="relative group">
                                                    <div className="absolute left-3 top-3 text-muted-foreground group-focus-within:text-purple-400 transition-colors">
                                                        <BrainCircuit className="w-5 h-5" />
                                                    </div>
                                                    <input
                                                        type="text"
                                                        value={customForm.aiRole}
                                                        onChange={(e) => setCustomForm({ ...customForm, aiRole: e.target.value })}
                                                        placeholder="e.g., Junior Developer"
                                                        className="w-full bg-background/50 border border-border group-hover:border-purple-500/30 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all font-medium"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>



                                    {/* 3. Context */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold uppercase text-muted-foreground ml-1">Scenario Context</label>
                                        <div className="relative group">
                                            <div className="absolute left-3 top-3.5 text-muted-foreground group-focus-within:text-primary transition-colors">
                                                <MessageSquare className="w-5 h-5" />
                                            </div>
                                            <textarea
                                                value={customForm.context}
                                                onChange={(e) => setCustomForm({ ...customForm, context: e.target.value })}
                                                placeholder="Describe the situation clearly. Example: 'I need to give negative feedback to a high performer who has been arriving late recently.'..."
                                                rows={4}
                                                className="w-full bg-background/50 border border-border group-hover:border-primary/30 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none leading-relaxed"
                                            />
                                        </div>
                                    </div>

                                    <div className="pt-4 flex justify-end">
                                        <button
                                            onClick={() => {
                                                if (!customForm.title || !customForm.userRole || !customForm.aiRole || !customForm.context) {
                                                    toast.error("Please fill in all fields")
                                                    return
                                                }

                                                // Dynamic mode based on toggle
                                                const scenario_type = customForm.sessionType === 'mentorship' ? 'mentorship' : 'coaching_sim'
                                                const session_mode = customForm.sessionType === 'mentorship' ? 'mentorship' : 'skill_assessment'
                                                const mode_param = customForm.sessionType === 'mentorship' ? 'mentorship' : 'evaluation'
                                                const flip_roles = customForm.sessionType === 'mentorship'

                                                handleStartSession({
                                                    role: customForm.userRole,
                                                    ai_role: customForm.aiRole,
                                                    scenario: customForm.context,
                                                    title: customForm.title,
                                                    scenario_type: scenario_type,
                                                    session_mode: session_mode,
                                                    ai_character: selectedCharacter,
                                                    mode: mode_param,
                                                    flip_roles: flip_roles
                                                })
                                            }}
                                            disabled={isStartingSession}
                                            className="w-full sm:w-auto px-10 py-4 rounded-full bg-gradient-to-r from-primary to-purple-600 text-white font-bold tracking-wide shadow-xl shadow-primary/20 hover:shadow-primary/40 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2.5"
                                        >
                                            {isStartingSession && startingScenarioTitle === customForm.title ? (
                                                <>
                                                    <Loader2 className="w-5 h-5 animate-spin" />
                                                    Initializing Simulation...
                                                </>
                                            ) : isStartingSession ? (
                                                'Initializing Simulation...'
                                            ) : (
                                                <>
                                                    Start Simulation
                                                    <Swords className="w-5 h-5" />
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </motion.div >
            </main >
        </div >
    )
}
