
import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { supabase } from '../lib/supabase';

const AuthCallback: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState('Verifying your email...');
    const handled = useRef(false);

    useEffect(() => {
        if (handled.current) return;
        handled.current = true;

        // Determine the callback type from hash or query params
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const type = hashParams.get('type') || searchParams.get('type') || '';
        const errorDescription = hashParams.get('error_description') || searchParams.get('error_description');

        if (errorDescription) {
            setStatus('error');
            setMessage(errorDescription);
            toast.error(errorDescription);
            return;
        }

        const redirectOnSuccess = (callbackType: string) => {
            if (callbackType === 'recovery') {
                setStatus('success');
                setMessage('Verified! Redirecting to reset password...');
                toast.success('Email verified! Please set your new password.');
                setTimeout(() => navigate('/reset-password'), 1500);
            } else if (callbackType === 'signup' || callbackType === 'email') {
                setStatus('success');
                setMessage('Email confirmed! Redirecting to login...');
                toast.success('Email confirmed successfully!');
                setTimeout(() => navigate('/login'), 1500);
            } else {
                setStatus('success');
                setMessage('Verified! Redirecting...');
                setTimeout(() => navigate('/practice'), 1500);
            }
        };

        // Handle PKCE flow: exchange code from query params
        const code = searchParams.get('code');
        if (code) {
            supabase.auth.exchangeCodeForSession(code).then(({ error }) => {
                if (error) {
                    console.error('Code exchange error:', error);
                    setStatus('error');
                    setMessage(error.message || 'Verification failed');
                    toast.error(error.message || 'Verification failed');
                } else {
                    redirectOnSuccess(type);
                }
            });
            return;
        }

        // Handle implicit flow: tokens in hash fragment
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        if (accessToken && refreshToken) {
            supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken }).then(({ error }) => {
                if (error) {
                    console.error('Set session error:', error);
                    setStatus('error');
                    setMessage(error.message || 'Verification failed');
                    toast.error(error.message || 'Verification failed');
                } else {
                    redirectOnSuccess(type);
                }
            });
            return;
        }

        // Fallback: Supabase detectSessionInUrl may have already processed the tokens.
        // Listen for the session to appear.
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            if (session) {
                subscription.unsubscribe();
                redirectOnSuccess(type);
            }
        });

        // Also check if a session already exists right now
        supabase.auth.getSession().then(({ data: { session } }) => {
            if (session) {
                subscription.unsubscribe();
                redirectOnSuccess(type);
            }
        });

        // Timeout: if nothing resolves after 10s, show error
        const timeout = setTimeout(() => {
            subscription.unsubscribe();
            if (status === 'loading') {
                setStatus('error');
                setMessage('Verification timed out. The link may be invalid or expired.');
            }
        }, 10000);

        return () => {
            clearTimeout(timeout);
            subscription.unsubscribe();
        };
    }, [navigate, searchParams]);

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden hero-ultra-modern">
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[100px] animate-pulse-glow" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[100px] animate-pulse-glow" style={{ animationDelay: '1s' }} />
            </div>

            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md card-ultra-glass relative z-10 text-center py-12"
            >
                {status === 'loading' && (
                    <>
                        <Loader2 className="w-16 h-16 text-purple-400 mx-auto mb-4 animate-spin" />
                        <h2 className="text-2xl font-bold text-foreground mb-2">Processing</h2>
                        <p className="text-muted-foreground">{message}</p>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                        <h2 className="text-2xl font-bold text-foreground mb-2">Success!</h2>
                        <p className="text-muted-foreground">{message}</p>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
                        <h2 className="text-2xl font-bold text-foreground mb-2">Verification Failed</h2>
                        <p className="text-muted-foreground mb-6">{message}</p>
                        <button
                            onClick={() => navigate('/login')}
                            className="btn-premium inline-flex items-center gap-2"
                        >
                            Back to Login
                        </button>
                    </>
                )}
            </motion.div>
        </div>
    );
};

export default AuthCallback;
