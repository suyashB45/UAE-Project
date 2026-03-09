"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Mic, Square, ArrowLeft, Clock, User, Bot, Send, Sparkles, History, X, Loader2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { getApiUrl } from "@/lib/api"
import { supabase } from "@/lib/supabase"

interface TranscriptMessage {
    role: "user" | "assistant"
    content: string
}

interface SessionData {
    role: string
    ai_role: string
    scenario: string
    createdAt: string
    transcript: TranscriptMessage[]
    sessionId?: string
    ai_character?: string
    multi_characters?: boolean
    characters?: CharacterConfig[]
}

interface CharacterConfig {
    name: string
    label: string
    voice: string
    color: string
}

interface ConversationState {
    transcript: TranscriptMessage[]
    isRecording: boolean
    isProcessing: boolean
    turnCount: number
    sessionData: SessionData | null
    elapsedSeconds: number
    currentDraft: string
    interimText: string  // Real-time text preview while speaking
    showTranscript: boolean
}

const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
}

export default function Conversation() {
    const params = useParams()
    const navigate = useNavigate()
    const sessionId = params.sessionId as string
    const recognitionRef = useRef<any>(null)
    const transcriptEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const sessionEndedRef = useRef(false)
    const ttsAbortRef = useRef<AbortController | null>(null)

    const [state, setState] = useState<ConversationState>({
        transcript: [],
        isRecording: false,
        isProcessing: false,
        turnCount: 0,
        sessionData: null,
        elapsedSeconds: 0,
        currentDraft: "",
        interimText: "",
        showTranscript: false,
    })
    const [isAiSpeaking, setIsAiSpeaking] = useState(false)
    const [showEndConfirm, setShowEndConfirm] = useState(false)
    const [isEnding, setIsEnding] = useState(false)
    const [multiCharacters, setMultiCharacters] = useState(false)
    const [characters, setCharacters] = useState<CharacterConfig[]>([])

    // Helper: Parse character-labeled lines from AI response
    const parseCharacterLines = (text: string): { char: string; text: string; voice: string; color: string }[] => {
        if (!multiCharacters || !characters.length) return [{ char: '', text, voice: 'fable', color: 'blue' }]

        const lines = text.split('\n').filter(l => l.trim())
        const parsed: { char: string; text: string; voice: string; color: string }[] = []

        for (const line of lines) {
            let matched = false
            for (const c of characters) {
                // Match [CharName]: or CharName:
                const regex = new RegExp(`^\\[?${c.name}\\]?:\\s*(.+)`, 'i')
                const match = line.match(regex)
                if (match) {
                    parsed.push({ char: c.name, text: match[1].trim(), voice: c.voice, color: c.color })
                    matched = true
                    break
                }
            }
            if (!matched && line.trim()) {
                // Append to last character if no label
                if (parsed.length > 0) {
                    parsed[parsed.length - 1].text += ' ' + line.trim()
                } else {
                    parsed.push({ char: characters[0]?.name || '', text: line.trim(), voice: characters[0]?.voice || 'fable', color: characters[0]?.color || 'blue' })
                }
            }
        }
        return parsed.length > 0 ? parsed : [{ char: '', text, voice: 'fable', color: 'blue' }]
    }

    // Scroll to bottom of transcript only if it's open
    useEffect(() => {
        if (state.showTranscript) {
            transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [state.transcript, state.currentDraft, state.showTranscript]);

    useEffect(() => {
        const timer = setInterval(() => {
            setState(prev => ({ ...prev, elapsedSeconds: prev.elapsedSeconds + 1 }))
        }, 1000)
        return () => clearInterval(timer)
    }, [])

    const mediaRecorderRef = useRef<MediaRecorder | null>(null)

    // State for user's uploaded audio URL
    const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null)
    const audioRef = useRef<HTMLAudioElement | null>(null)

    // Audio playback for AI response
    const aiAudioRef = useRef<HTMLAudioElement | null>(null)

    const speakText = async (text: string, forcedCharacter?: string, forceVoice?: string) => {
        // Don't start TTS if session has ended
        if (sessionEndedRef.current) {
            console.warn("[TTS] Skipped — session ended")
            return
        }

        try {
            // Determine voice: explicit override > character-based > default
            const voice = forceVoice || (forcedCharacter === 'sarah' || state.sessionData?.ai_character === 'sarah' ? 'nova' : 'fable')

            setIsAiSpeaking(true)

            // Abort any previous TTS request
            if (ttsAbortRef.current) ttsAbortRef.current.abort()
            const ttsController = new AbortController()
            ttsAbortRef.current = ttsController

            console.log("[TTS] Fetching audio...", { voice, textLen: text.length })
            const response = await fetch(getApiUrl('/api/speak'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice }),
                signal: ttsController.signal
            })

            if (!response.ok) throw new Error(`TTS failed: ${response.status}`)

            // Don't play if session ended while fetching
            if (sessionEndedRef.current) {
                setIsAiSpeaking(false)
                return
            }

            const blob = await response.blob()
            console.log("[TTS] Audio received:", blob.size, "bytes, type:", blob.type)
            const url = URL.createObjectURL(blob)

            if (aiAudioRef.current) {
                aiAudioRef.current.pause()
                aiAudioRef.current = null
            }

            const audio = new Audio(url)
            aiAudioRef.current = audio

            // Wait for audio to finish playing before resolving
            // This ensures sequential playback in multi-character mode
            await new Promise<void>((resolve) => {
                audio.onended = () => {
                    setIsAiSpeaking(false)
                    URL.revokeObjectURL(url)
                    resolve()
                }

                audio.onerror = (e) => {
                    setIsAiSpeaking(false)
                    console.error("[TTS] Audio playback error:", e)
                    URL.revokeObjectURL(url)
                    resolve()
                }

                audio.play().catch((err) => {
                    setIsAiSpeaking(false)
                    console.error("[TTS] audio.play() rejected:", err)
                    URL.revokeObjectURL(url)
                    resolve()
                })
            })

        } catch (error) {
            console.error("TTS Error:", error)
            setIsAiSpeaking(false)
        }
    }

    // Speak multi-character text with different voices sequentially
    const speakMultiCharacter = async (text: string) => {
        if (sessionEndedRef.current) return
        const parts = parseCharacterLines(text)
        for (const part of parts) {
            if (sessionEndedRef.current) break
            await speakText(part.text, undefined, part.voice)
        }
    }

    // Reset sessionEnded on mount, clean up on unmount
    useEffect(() => {
        sessionEndedRef.current = false
        return () => {
            sessionEndedRef.current = true
            if (ttsAbortRef.current) ttsAbortRef.current.abort()
            if (aiAudioRef.current) {
                aiAudioRef.current.pause()
                aiAudioRef.current = null
            }
        }
    }, [])

    useEffect(() => {
        const storedData = localStorage.getItem(`session_${sessionId}`)
        if (storedData) {
            const sessionData: SessionData = JSON.parse(storedData)

            const initialTranscript = sessionData.transcript.length > 0
                ? sessionData.transcript
                : [{
                    role: "assistant",
                    content: `Hi! I'm your AI coach. Today we'll practice: ${sessionData.scenario}. I'll play the role of ${sessionData.ai_role} to give you realistic practice, and I'll offer coaching tips along the way. Ready when you are!`
                }]

            setState((prev) => ({
                ...prev,
                sessionData,
                transcript: initialTranscript as TranscriptMessage[],
            }))

            // Set multi-character state
            if (sessionData.multi_characters && sessionData.characters) {
                setMultiCharacters(true)
                setCharacters(sessionData.characters)
            }

            // Speak initial message
            const latestMsg = initialTranscript[initialTranscript.length - 1]
            if (latestMsg.role === 'assistant' && initialTranscript.length === 1) {
                const timer = setTimeout(() => {
                    if (sessionData.multi_characters && sessionData.characters) {
                        speakMultiCharacter(latestMsg.content)
                    } else {
                        speakText(latestMsg.content, sessionData.ai_character)
                    }
                }, 500)
                return () => clearTimeout(timer)
            }
        }
    }, [sessionId])

    useEffect(() => {
        return () => {
            if (audioRef.current) {
                audioRef.current.pause()
                audioRef.current = null
            }
            if (recognitionRef.current) {
                recognitionRef.current.stop()
            }
            // Ensure media recorder tracks are stopped (microphone off)
            if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
                mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
            }
            // Abort any pending API calls
            if (abortControllerRef.current) {
                abortControllerRef.current.abort()
            }
        }
    }, [])

    const stopRecording = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop()
        }
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop()
            if (mediaRecorderRef.current.stream) {
                mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop())
            }
        }
        setState((prev) => ({ ...prev, isRecording: false }))
    }, [])

    const startRecording = async () => {
        if (isAiSpeaking) return

        try {
            // Use MediaRecorder to capture audio and send to Whisper backend
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const audioChunks: Blob[] = []

            // Try to use a mime type supported by the browser
            const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
            const mediaRecorder = new MediaRecorder(stream, { mimeType })
            mediaRecorderRef.current = mediaRecorder

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data)
                }
            }

            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(track => track.stop())
                if (audioChunks.length === 0) return

                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })

                try {
                    setState(prev => ({ ...prev, isProcessing: true, interimText: "Transcribing..." }))

                    const formData = new FormData()
                    formData.append('file', audioBlob, 'audio.webm')
                    if (sessionId) formData.append('session_id', sessionId)

                    const response = await fetch(getApiUrl('/api/transcribe'), {
                        method: 'POST',
                        body: formData,
                        signal: abortControllerRef.current?.signal
                    })

                    if (!response.ok) throw new Error('Whisper API failed')

                    const data = await response.json()
                    const transcribedText = data.text?.trim()

                    if (data.audio_url) {
                        setLastAudioUrl(data.audio_url)
                    }

                    if (transcribedText) {
                        setState(prev => ({
                            ...prev,
                            currentDraft: prev.currentDraft + transcribedText + " ",
                            isProcessing: false,
                            interimText: ""
                        }))
                    } else {
                        setState(prev => ({ ...prev, isProcessing: false, interimText: "" }))
                    }
                } catch (error) {
                    console.error("Whisper STT Error:", error)
                    setState(prev => ({ ...prev, isProcessing: false, interimText: "" }))
                    toast.error("Transcription Error", {
                        description: "Could not transcribe audio via Whisper."
                    })
                }
            }

            mediaRecorder.onerror = () => {
                console.error("MediaRecorder error")
                stream.getTracks().forEach(track => track.stop())
                setState(prev => ({ ...prev, isRecording: false }))
            }

            mediaRecorder.start(1000)
            setState(prev => ({ ...prev, isRecording: true, interimText: "Recording..." }))

        } catch (error) {
            console.error("Error accessing microphone:", error)
            toast.error("Microphone Error", {
                description: "Unable to access microphone. Please check permissions."
            })
        }
    }

    const handleSend = async () => {
        const message = state.currentDraft.trim()
        if (!message) return

        stopRecording()

        setState((prev) => ({
            ...prev,
            transcript: [...prev.transcript, { role: "user", content: message }],
            currentDraft: "",
            isProcessing: true,
        }))

        try {
            // Abort previous pending request if any
            if (abortControllerRef.current) {
                abortControllerRef.current.abort()
            }
            const controller = new AbortController()
            abortControllerRef.current = controller

            // Get auth token for session persistence
            const { data: { session: authSession } } = await supabase.auth.getSession()
            const authHeaders: Record<string, string> = {
                'Content-Type': 'application/json'
            }
            if (authSession?.access_token) {
                authHeaders['Authorization'] = `Bearer ${authSession.access_token}`
            }

            // Call backend chat API
            const response = await fetch(getApiUrl(`/api/session/${sessionId}/chat`), {
                method: 'POST',
                headers: authHeaders,
                body: JSON.stringify({
                    message,
                    audio_url: lastAudioUrl // Send the audio we just saved
                }),
                signal: controller.signal
            })

            // Reset audio url for next turn
            setLastAudioUrl(null)

            if (!response.ok) {
                throw new Error("Failed to get AI response")
            }

            const data = await response.json()
            const aiResponse = data.follow_up

            setState((prev) => ({
                ...prev,
                transcript: [...prev.transcript, { role: "assistant", content: aiResponse }],
                turnCount: prev.turnCount + 1,
                isProcessing: false,
            }))

            if (multiCharacters) {
                speakMultiCharacter(aiResponse)
            } else {
                speakText(aiResponse)
            }

            // Update local storage
            if (state.sessionData) {
                const updated = {
                    ...state.sessionData,
                    transcript: [...state.sessionData.transcript,
                    { role: "user", content: message },
                    { role: "assistant", content: aiResponse }
                    ]
                }
                localStorage.setItem(`session_${sessionId}`, JSON.stringify(updated))
            }

        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.log("Request aborted")
                return
            }
            console.error("Conversation Error:", error)
            setState((prev) => ({ ...prev, isProcessing: false }))

            toast.error("Error", {
                description: "Something went wrong. Please try again."
            })
        }
    }

    const handleEndConversation = async () => {
        if (isEnding) return // Prevent double-clicks
        setIsEnding(true)

        // Mark session as ended to prevent any new TTS
        sessionEndedRef.current = true

        // Abort any in-flight TTS request
        if (ttsAbortRef.current) {
            ttsAbortRef.current.abort()
        }

        // Aggressively kill AI Speech
        if (aiAudioRef.current) {
            aiAudioRef.current.pause()
            aiAudioRef.current.currentTime = 0
            aiAudioRef.current = null
        }
        setIsAiSpeaking(false)

        // Aggressively kill network requests
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
        }

        // Aggressively kill microphone without triggering transcription
        if (mediaRecorderRef.current) {
            mediaRecorderRef.current.onstop = null
        }
        stopRecording()

        try {
            // Get auth token for session persistence
            const { data: { session: authSession } } = await supabase.auth.getSession()
            const authHeaders: Record<string, string> = {}
            if (authSession?.access_token) {
                authHeaders['Authorization'] = `Bearer ${authSession.access_token}`
            }

            // Call backend to complete session and generate report
            await fetch(getApiUrl(`/api/session/${sessionId}/complete`), {
                method: 'POST',
                headers: {
                    ...authHeaders,
                    'Content-Type': 'application/json'
                }
            })

            // Update localStorage for offline reference
            if (state.sessionData) {
                const updated = {
                    ...state.sessionData,
                    completed: true
                }
                localStorage.setItem(`session_${sessionId}`, JSON.stringify(updated))
            }

            // Navigate ONLY after the report generation is complete
            navigate(`/report/${sessionId}`)

        } catch (error) {
            console.error("Error completing session:", error)
            toast.error("Error", { description: "Failed to complete session. Navigating to report anyway." })
            setIsEnding(false)
            setShowEndConfirm(false)
            navigate(`/report/${sessionId}`) // Optional: still try to navigate if we want them to see partial data/error state
        }
    }

    // Get the latest message for captioning
    const lastMessage = state.transcript.length > 0 ? state.transcript[state.transcript.length - 1] : null

    return (
        <div className="min-h-screen bg-background text-foreground relative overflow-hidden flex flex-col font-sans transition-colors duration-500">
            {/* Animated Background */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-[20%] left-[20%] w-[600px] h-[600px] bg-primary/10 rounded-full blur-[120px] animate-pulse duration-[10s]" />
                <div className="absolute bottom-[20%] right-[20%] w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[120px] animate-pulse duration-[8s]" />

            </div>

            {/* Header - Mobile responsive */}
            <header className="relative z-50 px-3 sm:px-6 py-3 sm:py-6 flex justify-between items-center">
                <div className="flex items-center gap-2 sm:gap-4">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate("/practice")}
                        className="text-foreground hover:bg-muted/20 rounded-full w-9 h-9 sm:w-10 sm:h-10 border border-border backdrop-blur-md"
                    >
                        <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
                    </Button>
                    <div className="bg-card/50 backdrop-blur-xl px-3 sm:px-4 py-2 sm:py-2 rounded-full border border-border flex items-center gap-2 sm:gap-3 shadow-lg">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${state.isRecording ? 'bg-destructive animate-pulse shadow-[0_0_10px_oklch(from_var(--destructive)_l_c_h_/_0.5)]' : 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]'}`} />
                        <span className="text-xs sm:text-sm font-semibold tracking-wide text-foreground/80 hidden xs:inline">
                            {state.isRecording ? "Listening..." : isAiSpeaking ? "AI Speaking" : "Connected"}
                        </span>
                        <div className="w-px h-3 sm:h-4 bg-border" />
                        <Clock className="w-3 h-3 text-muted-foreground" />
                        <span className="text-xs sm:text-sm text-muted-foreground font-mono tracking-wider">{formatTime(state.elapsedSeconds)}</span>
                    </div>
                </div>

                <div className="flex gap-3">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setState(prev => ({ ...prev, showTranscript: true }))}
                        className="text-muted-foreground hover:text-foreground rounded-full bg-card/50 border border-border w-9 h-9 sm:w-10 sm:h-10 backdrop-blur-md"
                    >
                        <History className="h-5 w-5" />
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={() => setShowEndConfirm(true)}
                        disabled={isEnding}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-full px-4 sm:px-6 text-sm font-semibold backdrop-blur-md transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isEnding ? 'Ending...' : 'End Session'}
                    </Button>
                </div>
            </header>

            {/* Main Content - Voice Sphere */}
            <main className="flex-1 flex flex-col items-center justify-center relative z-10 p-4 sm:p-6 min-h-[400px] sm:min-h-[600px]">

                {/* The Sphere Container */}
                <div className="relative mb-8 sm:mb-16 group">
                    {/* Morphing Background Blob */}
                    <div className={`absolute -inset-8 sm:-inset-12 morph-blob blur-3xl transition-all duration-1000 ${state.isRecording
                        ? 'bg-destructive/20'
                        : isAiSpeaking
                            ? 'bg-primary/25'
                            : 'bg-indigo-500/10 dark:bg-indigo-500/10'
                        }`} />

                    {/* Ring Pulse Effect - Multiple Rings */}
                    {(state.isRecording || isAiSpeaking) && (
                        <>
                            <div className={`absolute -inset-4 rounded-full border-2 animate-ring-pulse ${state.isRecording ? 'border-destructive/40' : 'border-primary/40'
                                }`} />
                            <div className={`absolute -inset-4 rounded-full border-2 animate-ring-pulse ${state.isRecording ? 'border-destructive/40' : 'border-primary/40'
                                }`} style={{ animationDelay: '0.5s' }} />
                            <div className={`absolute -inset-4 rounded-full border-2 animate-ring-pulse ${state.isRecording ? 'border-destructive/40' : 'border-primary/40'
                                }`} style={{ animationDelay: '1s' }} />
                        </>
                    )}

                    {/* Outer Glow Ring */}
                    <motion.div
                        animate={{
                            scale: isAiSpeaking ? [1, 1.3, 1] : state.isProcessing ? [1, 1.1, 1] : 1,
                            opacity: isAiSpeaking ? [0.15, 0.3, 0.15] : state.isRecording ? 0.2 : 0.08
                        }}
                        transition={{ duration: isAiSpeaking ? 1.5 : 3, repeat: Infinity, ease: "easeInOut" }}
                        className={`absolute -inset-6 sm:-inset-8 rounded-full blur-2xl transition-colors duration-700 ${state.isRecording
                            ? 'bg-gradient-to-br from-destructive/40 to-rose-600/30'
                            : isAiSpeaking
                                ? 'bg-gradient-to-br from-primary/30 to-purple-500/30'
                                : 'bg-primary/5 dark:bg-blue-500/15'
                            }`}
                    />

                    {/* Inner Border Ring */}
                    <motion.div
                        animate={{
                            scale: isAiSpeaking ? [1, 1.08, 1] : 1,
                            rotate: state.isProcessing ? 360 : 0
                        }}
                        transition={{
                            scale: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
                            rotate: { duration: 8, repeat: Infinity, ease: "linear" }
                        }}
                        className={`absolute -inset-4 sm:-inset-5 rounded-full border transition-colors duration-500 ${state.isRecording
                            ? 'border-destructive/30'
                            : state.isProcessing
                                ? 'border-dashed border-primary/40'
                                : 'border-border'
                            }`}
                    />

                    {/* Core Sphere */}
                    <motion.div
                        animate={{
                            scale: isAiSpeaking ? [1, 1.04, 1] : state.isRecording ? [1, 1.02, 1] : 1,
                        }}
                        transition={{ duration: isAiSpeaking ? 0.8 : 2, repeat: Infinity, ease: "easeInOut" }}
                        className={`w-44 h-44 sm:w-52 sm:h-52 rounded-full shadow-2xl flex items-center justify-center relative overflow-hidden transition-all duration-700 border border-border ${!state.isRecording && !isAiSpeaking && !state.isProcessing ? 'animate-breathe' : ''
                            }`}
                        style={{
                            background: state.isRecording
                                ? "linear-gradient(135deg, oklch(from var(--destructive) l c h) 0%, oklch(from var(--destructive) l c h / 0.8) 100%)"
                                : isAiSpeaking
                                    ? "linear-gradient(135deg, oklch(from var(--primary) l c h) 0%, oklch(from var(--primary) l c h / 0.8) 100%)"
                                    : state.isProcessing
                                        ? "linear-gradient(135deg, oklch(from var(--primary) l c h / 0.8) 0%, oklch(from var(--primary) l c h) 100%)"
                                        : "var(--card)"
                        }}
                    >
                        {/* Internal Shine/Reflection */}
                        <div className="absolute top-0 right-0 w-full h-full bg-gradient-to-bl from-white/25 via-transparent to-transparent rounded-full" />
                        <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-black/50 to-transparent rounded-full" />

                        {/* Subtle Inner Glow */}
                        <div className={`absolute inset-4 rounded-full blur-xl transition-opacity duration-500 ${isAiSpeaking ? 'bg-primary/20 opacity-100' : state.isRecording ? 'bg-destructive/20 opacity-100' : 'opacity-0'
                            }`} />

                        {/* Content: Icon or Audio Visualizer */}
                        <div className="relative z-10 transition-transform duration-300 flex items-center justify-center">
                            {state.isRecording ? (
                                /* Audio Visualizer Bars while Recording */
                                <div className="flex items-end justify-center gap-1 h-16">
                                    {[...Array(9)].map((_, i) => (
                                        <div
                                            key={i}
                                            className="audio-bar w-1.5 rounded-full"
                                            style={{
                                                height: `${30 + Math.random() * 40}%`,
                                                background: 'linear-gradient(180deg, var(--background) 0%, var(--destructive) 100%)',
                                                animationDelay: `${i * 0.1}s`
                                            }}
                                        />
                                    ))}
                                </div>
                            ) : isAiSpeaking ? (
                                /* Audio Visualizer for AI Speaking */
                                <div className="flex items-end justify-center gap-1 h-16">
                                    {[...Array(9)].map((_, i) => (
                                        <div
                                            key={i}
                                            className="audio-bar w-1.5 rounded-full"
                                            style={{
                                                animationDelay: `${i * 0.1}s`
                                            }}
                                        />
                                    ))}
                                </div>
                            ) : state.isProcessing ? (
                                <Sparkles className="w-16 h-16 text-primary drop-shadow-[0_4px_8px_rgba(0,0,0,0.1)] animate-spin-slow" />
                            ) : (
                                <Bot className="w-16 h-16 text-muted-foreground drop-shadow-[0_4px_8px_rgba(0,0,0,0.1)] group-hover:text-foreground transition-colors" />
                            )}
                        </div>
                    </motion.div>
                </div>

                {/* AI Spoken Text Box */}
                <div className="max-w-2xl w-full px-4 relative z-20">
                    <AnimatePresence mode="wait">
                        {state.currentDraft ? (
                            <motion.div
                                key="draft"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-5 sm:p-6 shadow-lg"
                            >
                                <div className="flex items-center gap-2 mb-3">
                                    <div className="w-2 h-2 rounded-full bg-destructive animate-pulse" />
                                    <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Listening...</span>
                                </div>
                                <p className="text-base sm:text-lg text-foreground leading-relaxed">
                                    "{state.currentDraft}"
                                    <span className="inline-block w-2 h-5 bg-primary rounded-full animate-pulse ml-1 align-middle" />
                                </p>
                            </motion.div>
                        ) : lastMessage ? (
                            <motion.div
                                key="last-msg"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="space-y-3 max-h-[300px] overflow-y-auto"
                            >
                                {lastMessage.role === 'assistant' && multiCharacters ? (
                                    /* Multi-character: render each character's line separately */
                                    parseCharacterLines(lastMessage.content).map((part, idx) => (
                                        <div
                                            key={idx}
                                            className={`backdrop-blur-xl border rounded-2xl p-4 sm:p-5 shadow-lg ${part.color === 'pink'
                                                ? 'bg-pink-500/10 border-pink-500/20'
                                                : 'bg-blue-500/10 border-blue-500/20'
                                                }`}
                                        >
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className={`p-1.5 rounded-lg ${part.color === 'pink' ? 'bg-pink-500/10' : 'bg-blue-500/10'
                                                    }`}>
                                                    <Bot className={`w-3.5 h-3.5 ${part.color === 'pink' ? 'text-pink-500' : 'text-blue-500'
                                                        }`} />
                                                </div>
                                                <span className={`text-xs font-bold uppercase tracking-widest ${part.color === 'pink' ? 'text-pink-500' : 'text-blue-500'
                                                    }`}>
                                                    {part.char}
                                                </span>
                                            </div>
                                            <p className="text-base sm:text-lg leading-relaxed text-foreground font-medium">
                                                {part.text}
                                            </p>
                                        </div>
                                    ))
                                ) : (
                                    /* Single character: original rendering */
                                    <div className={`backdrop-blur-xl border rounded-2xl p-5 sm:p-6 shadow-lg ${lastMessage.role === 'assistant'
                                        ? 'bg-primary/5 border-primary/20'
                                        : 'bg-card/80 border-border'
                                        }`}>
                                        <div className="flex items-center gap-2 mb-3">
                                            <div className={`p-1.5 rounded-lg ${lastMessage.role === 'assistant' ? 'bg-primary/10' : 'bg-muted/50'}`}>
                                                {lastMessage.role === 'assistant' ? <Bot className="w-3.5 h-3.5 text-primary" /> : <User className="w-3.5 h-3.5 text-muted-foreground" />}
                                            </div>
                                            <span className={`text-xs font-bold uppercase tracking-widest ${lastMessage.role === 'assistant' ? 'text-primary' : 'text-muted-foreground'}`}>
                                                {lastMessage.role === 'assistant' ? 'AI Coach' : 'You'}
                                            </span>
                                            {lastMessage.role === 'assistant' && isAiSpeaking && (
                                                <div className="flex items-center gap-0.5 ml-auto">
                                                    {[...Array(4)].map((_, i) => (
                                                        <div key={i} className="w-1 bg-primary rounded-full animate-pulse" style={{ height: `${8 + Math.random() * 8}px`, animationDelay: `${i * 0.15}s` }} />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <p className={`text-base sm:text-lg leading-relaxed ${lastMessage.role === 'assistant'
                                            ? 'text-foreground font-medium'
                                            : 'text-muted-foreground'
                                            }`}>
                                            {lastMessage.content}
                                        </p>
                                    </div>
                                )}
                            </motion.div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="bg-card/50 backdrop-blur-xl border border-dashed border-border rounded-2xl p-5 sm:p-6 text-center"
                            >
                                <p className="text-muted-foreground text-base font-medium">Tap the microphone to start the conversation</p>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

            </main>

            {/* Bottom Controls - Mobile responsive */}
            <div className="relative z-50 p-4 sm:p-10 flex justify-center items-center gap-4 sm:gap-10">

                {/* Cancel Button (Hidden but usable for layout balance if needed, or keeping simplified) */}
                <div className="w-16 sm:w-20 hidden md:block" />

                <div className="relative group">
                    {/* Ripple Effect */}
                    {state.isRecording && (
                        <div className="absolute inset-0 rounded-full bg-destructive/30 animate-ping duration-1000" />
                    )}

                    <Button
                        onClick={state.isRecording ? stopRecording : startRecording}
                        disabled={isAiSpeaking || state.isProcessing}
                        className={`h-16 w-16 sm:h-24 sm:w-24 rounded-full shadow-2xl transition-all duration-300 relative z-10 border-4 border-background ${state.isRecording
                            ? "bg-gradient-to-br from-destructive to-red-600 hover:from-destructive hover:to-red-500 scale-110 shadow-[0_0_40px_oklch(from_var(--destructive)_l_c_h_/_0.4)]"
                            : "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 shadow-[0_0_30px_oklch(from_var(--primary)_l_c_h_/_0.3)]"
                            }`}
                    >
                        {state.isRecording ? (
                            <Square className="w-6 h-6 sm:w-10 sm:h-10 fill-current text-white" />
                        ) : (
                            <Mic className="w-6 h-6 sm:w-10 sm:h-10 text-white" />
                        )}
                    </Button>
                </div>

                <div className="w-16 sm:w-20 flex justify-start">
                    <AnimatePresence>
                        {state.currentDraft && !state.isProcessing && (
                            <motion.div
                                initial={{ scale: 0, opacity: 0, x: -20 }}
                                animate={{ scale: 1, opacity: 1, x: 0 }}
                                exit={{ scale: 0, opacity: 0, x: -20 }}
                            >
                                <Button
                                    onClick={handleSend}
                                    className="h-12 w-12 sm:h-16 sm:w-16 rounded-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-500 text-white shadow-xl shadow-primary/20 border border-border"
                                >
                                    <Send className="w-5 h-5 sm:w-7 sm:h-7 ml-0.5" />
                                </Button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Transcript Drawer / Panel */}
            <AnimatePresence>
                {state.showTranscript && (
                    <div className="fixed inset-0 z-[100] flex justify-end">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setState(prev => ({ ...prev, showTranscript: false }))}
                            className="absolute inset-0 bg-background/60 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ x: "100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "100%" }}
                            transition={{ type: "spring", damping: 30, stiffness: 300 }}
                            className="relative w-full max-w-lg h-full bg-card/90 backdrop-blur-xl border-l border-border shadow-2xl flex flex-col"
                        >
                            <div className="p-6 border-b border-border flex justify-between items-center bg-card/5">
                                <h3 className="text-xl font-bold text-foreground flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                                        <History className="w-5 h-5 text-primary" />
                                    </div>
                                    Session Transcript
                                </h3>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => setState(prev => ({ ...prev, showTranscript: false }))}
                                    className="hover:bg-muted/10 rounded-full"
                                >
                                    <X className="w-5 h-5 text-muted-foreground" />
                                </Button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide">
                                {state.transcript.map((msg, idx) => (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.05 * idx }}
                                        key={idx}
                                        className={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                                    >
                                        {msg.role === 'assistant' && multiCharacters ? (
                                            /* Multi-character transcript entries */
                                            <div className="space-y-2 w-full">
                                                {parseCharacterLines(msg.content).map((part, pIdx) => (
                                                    <div key={pIdx}>
                                                        <div className={`flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest mb-1 ${part.color === 'pink' ? 'text-pink-500' : 'text-blue-500'
                                                            }`}>
                                                            {part.char} <div className={`w-6 h-[1px] ${part.color === 'pink' ? 'bg-pink-500/30' : 'bg-blue-500/30'}`}></div>
                                                        </div>
                                                        <div className={`p-4 rounded-2xl max-w-[85%] text-sm leading-relaxed backdrop-blur-md border shadow-lg rounded-tl-sm ${part.color === 'pink'
                                                            ? 'bg-pink-500/10 border-pink-500/20 text-foreground'
                                                            : 'bg-blue-500/10 border-blue-500/20 text-foreground'
                                                            }`}>
                                                            {part.text}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            /* Original single-character transcript entries */
                                            <>
                                                <div className={`flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest ${msg.role === 'user' ? 'text-muted-foreground flex-row-reverse' : 'text-primary'}`}>
                                                    {msg.role === 'user' ? (
                                                        <>You <div className="w-6 h-[1px] bg-border"></div></>
                                                    ) : (
                                                        <>AI Coach <div className="w-6 h-[1px] bg-primary/30"></div></>
                                                    )}
                                                </div>

                                                <div className={`p-5 rounded-2xl max-w-[85%] text-sm leading-relaxed backdrop-blur-md border shadow-lg ${msg.role === 'user'
                                                    ? 'bg-card border-border text-foreground rounded-tr-sm'
                                                    : 'bg-primary/10 border-primary/20 text-foreground rounded-tl-sm'
                                                    }`}>
                                                    {msg.content}
                                                </div>
                                            </>
                                        )}
                                    </motion.div>
                                ))}
                                <div ref={transcriptEndRef} />
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* End Session Confirmation Modal */}
            <AnimatePresence>
                {showEndConfirm && !isEnding && (
                    <div className="fixed inset-0 z-[200] flex items-center justify-center">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setShowEndConfirm(false)}
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.9, y: 20 }}
                            transition={{ type: "spring", damping: 25, stiffness: 300 }}
                            className="relative bg-card border border-border rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl"
                        >
                            <div className="text-center">
                                <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5">
                                    <Square className="w-6 h-6 text-red-500" />
                                </div>
                                <h3 className="text-xl font-bold text-foreground mb-2">End Session?</h3>
                                <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
                                    Are you sure you want to end this session? Your report will be generated automatically.
                                </p>
                                <div className="flex gap-3">
                                    <Button
                                        variant="ghost"
                                        onClick={() => setShowEndConfirm(false)}
                                        disabled={isEnding}
                                        className="flex-1 rounded-xl border border-border hover:bg-muted/20 font-semibold"
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="destructive"
                                        onClick={handleEndConversation}
                                        disabled={isEnding}
                                        className="flex-1 rounded-xl bg-red-500 hover:bg-red-600 text-white font-semibold shadow-lg shadow-red-500/20 flex items-center justify-center gap-2"
                                    >
                                        Yes, End Session
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Full Page Generation Loader */}
            <AnimatePresence>
                {isEnding && (
                    <div className="fixed inset-0 z-[300] flex items-center justify-center">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-background/80 backdrop-blur-md"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="relative bg-card border border-primary/20 rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl shadow-primary/10 flex flex-col items-center text-center"
                        >
                            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
                                <Loader2 className="w-8 h-8 text-primary animate-spin" />
                            </div>
                            <h3 className="text-2xl font-bold text-foreground mb-2">Generating Report</h3>
                            <p className="text-muted-foreground text-sm leading-relaxed">
                                Please wait while our AI analyzes your conversation, determines your scorecard, and compiles actionable feedback. This may take up to 20 seconds.
                            </p>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    )
}


