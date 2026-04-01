import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ROUTES } from "../constants/routes";
import { getQuiz, submitQuizAttempt, getSkillProfile, Quiz, SkillProfile } from "../services/quizApi";
import { usePostHog } from "@posthog/react";
import AppBreadcrumb from "../components/AppBreadcrumb";
import DataLoadingState from "../components/DataLoadingState";
import QuizSkeleton from "../components/skeletons/QuizSkeleton";

export default function QuizPage() {
    const { courseId } = useParams();
    const navigate = useNavigate();
    const posthog = usePostHog();

    const [quiz, setQuiz] = useState<Quiz | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [submitting, setSubmitting] = useState(false);

    const [result, setResult] = useState<{
        score: number;
        passed: boolean;
        xp_awarded: number;
        total_xp: number;
        current_level: number;
        leveled_up: boolean;
    } | null>(null);
    const [newProfile, setNewProfile] = useState<SkillProfile | null>(null);

    // To track submitted answers for result explanations
    const [submittedAnswers, setSubmittedAnswers] = useState<Record<string, string>>({});

    useEffect(() => {
        if (!courseId) return;

        setQuiz(null);
        setResult(null);
        setNewProfile(null);
        setAnswers({});
        setSubmittedAnswers({});
        setCurrentQuestionIndex(0);
        setLoading(true);
        setError(null);

        getQuiz(courseId)
            .then((data) => {
                if (!data) {
                    setError("Failed to load quiz. The generator may be temporarily unavailable.");
                } else {
                    setQuiz(data);
                }
            })
            .catch((err) => {
                setError(err.message || "An error occurred fetching the quiz.");
            })
            .finally(() => {
                setLoading(false);
            });
    }, [courseId]);

    const handleOptionSelect = (option: string) => {
        if (!quiz || !quiz.questions[currentQuestionIndex]) return;
        const questionId = quiz.questions[currentQuestionIndex].id || `q${currentQuestionIndex}`;

        setAnswers((prev) => ({
            ...prev,
            [questionId]: option,
        }));
    };

    const handleNext = async () => {
        if (!quiz) return;

        if (currentQuestionIndex < quiz.questions.length - 1) {
            setCurrentQuestionIndex((prev) => prev + 1);
            return;
        }

        setSubmitting(true);
        setSubmittedAnswers({ ...answers });

        try {
            const submissionResult = await submitQuizAttempt(courseId!, answers);
            if (submissionResult) {
                setResult({
                    score: submissionResult.score,
                    passed: submissionResult.passed,
                    xp_awarded: submissionResult.xp_awarded ?? 0,
                    total_xp: submissionResult.total_xp ?? 0,
                    current_level: submissionResult.current_level ?? 1,
                    leveled_up: submissionResult.leveled_up ?? false,
                });
                posthog?.capture('quiz_submitted', {
                    course_id: courseId,
                    score: submissionResult.score,
                    passed: submissionResult.passed,
                    total_questions: quiz?.questions.length,
                });

                const updatedProfile = await getSkillProfile(courseId!);
                setNewProfile(updatedProfile);
            } else {
                setError("Failed to submit quiz attempt.");
            }
        } catch (err: any) {
            const msg = err.message || "Error submitting quiz";
            setError(msg);
            toast.error(msg);
            posthog?.captureException(err);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div style={{ backgroundColor: "#0a0a0f", minHeight: "100vh" }}>
                <DataLoadingState>
                    <QuizSkeleton />
                </DataLoadingState>
            </div>
        );
    }

    if (error) {
        return (
            <div className="quiz-page-root flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <style>{`
                    .quiz-page-root { --bg-primary: #0a0a0f; background-color: var(--bg-primary); }
                `}</style>
                <div className="max-w-md mx-auto p-8 rounded-xl border border-red-900/50 bg-red-900/10 text-center">
                    <div className="text-4xl mb-4 text-red-500">⚠️</div>
                    <h2 className="text-xl font-semibold text-red-400 mb-2">Quiz Load Error</h2>
                    <p className="text-red-300/80 mb-6">{error}</p>
                    <button
                        onClick={() => navigate(-1)}
                        className="px-6 py-2 rounded font-medium transition-colors"
                        style={{ backgroundColor: 'var(--accent-primary)', color: 'white' }}
                    >
                        Go Back
                    </button>
                </div>
            </div>
        );
    }

    if (!quiz) return null;

    // --- RESULT SCREEN ---
    if (result) {
        const roadmapId = courseId?.split(":")[0] ?? "";
        let scoreColor = '#ef4444'; // red
        if (result.score >= 75) scoreColor = '#22c55e'; // green
        else if (result.score >= 50) scoreColor = '#eab308'; // yellow

        const retakeButton = (
            <button
                onClick={() => {
                    posthog?.capture('quiz_retaken', { course_id: courseId, previous_score: result?.score });
                    setResult(null);
                    setNewProfile(null);
                    setAnswers({});
                    setSubmittedAnswers({});
                    setCurrentQuestionIndex(0);
                }}
                className="px-8 py-3 rounded-lg font-bold border transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)', backgroundColor: 'transparent' }}
                onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--accent-primary)' }}
                onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--border)' }}
            >
                Retake Quiz
            </button>
        );

        return (
            <div className="quiz-page-root">
                <style>{`
                    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
                    .quiz-page-root {
                        --bg-primary: #0a0a0f;
                        --bg-card: #111118;
                        --accent-primary: #6366f1;
                        --text-primary: #f1f5f9;
                        --text-muted: #64748b;
                        --border: #1e1e2e;

                        background-color: var(--bg-primary);
                        color: var(--text-primary);
                        font-family: 'DM Sans', sans-serif;
                        min-height: 100vh;
                        padding-bottom: 4rem;
                    }
                    .title-font { font-family: 'Sora', sans-serif; }
                    .dark-card {
                        background-color: var(--bg-card);
                        border: 1px solid var(--border);
                        border-radius: 0.75rem;
                    }
                `}</style>

                <div className="max-w-3xl mx-auto pt-12 px-4">
                    {result.passed ? (
                        /* ── PASSED: Course Completed celebration ── */
                        <div
                            className="rounded-2xl p-8 sm:p-10 text-center mb-8 relative overflow-hidden"
                            style={{
                                background: 'linear-gradient(135deg, #052e16 0%, #14532d 50%, #166534 100%)',
                                border: '1px solid rgba(34,197,94,0.3)',
                            }}
                        >
                            <div
                                className="absolute top-0 right-0 w-64 h-64 rounded-full pointer-events-none"
                                style={{ background: 'radial-gradient(circle, rgba(34,197,94,0.08) 0%, transparent 70%)', transform: 'translate(30%,-30%)' }}
                            />
                            <div className="relative z-10">
                                <div className="text-5xl mb-4">🎉</div>
                                <div className="text-sm font-bold uppercase tracking-widest mb-2" style={{ color: 'rgba(134,239,172,0.7)' }}>
                                    Course Completed
                                </div>
                                <h2 className="title-font text-3xl sm:text-4xl font-bold text-white mb-1">
                                    {Math.round(result.score)}% Score
                                </h2>
                                <p className="text-sm mb-6" style={{ color: 'rgba(134,239,172,0.6)' }}>
                                    You've mastered this topic. This course is now marked as complete.
                                </p>

                                {/* XP + level-up badges */}
                                {result.xp_awarded > 0 && (
                                    <div className="flex items-center justify-center gap-3 mb-6 flex-wrap">
                                        <div
                                            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full font-bold text-sm"
                                            style={{ backgroundColor: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.4)', color: '#a5b4fc' }}
                                        >
                                            +{result.xp_awarded} XP
                                        </div>
                                        {result.leveled_up && (
                                            <div
                                                className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full font-bold text-sm"
                                                style={{ backgroundColor: 'rgba(234,179,8,0.2)', border: '1px solid rgba(234,179,8,0.4)', color: '#fde68a' }}
                                            >
                                                🎊 Level {result.current_level}!
                                            </div>
                                        )}
                                        <div
                                            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full font-bold text-sm"
                                            style={{ backgroundColor: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.6)' }}
                                        >
                                            {result.total_xp} XP total
                                        </div>
                                    </div>
                                )}

                                {/* CTAs */}
                                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                                    <button
                                        onClick={() => navigate(`/roadmap/${roadmapId}`)}
                                        className="px-8 py-3 rounded-lg font-bold text-sm transition-all shadow-md"
                                        style={{ backgroundColor: '#22c55e', color: 'white' }}
                                        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#16a34a'}
                                        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#22c55e'}
                                    >
                                        View Learning Path →
                                    </button>
                                    <button
                                        onClick={() => navigate('/dashboard')}
                                        className="px-8 py-3 rounded-lg font-bold text-sm border transition-colors"
                                        style={{ borderColor: 'rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.7)', backgroundColor: 'transparent' }}
                                        onMouseOver={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)'; e.currentTarget.style.color = 'white'; }}
                                        onMouseOut={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
                                    >
                                        Go to Dashboard
                                    </button>
                                    {retakeButton}
                                </div>
                            </div>
                        </div>
                    ) : (
                        /* ── FAILED: Standard results card ── */
                        <div className="dark-card p-10 text-center mb-8">
                            <div className="text-sm font-bold uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)' }}>Quiz Results</div>
                            <div className="title-font font-bold text-7xl md:text-8xl mb-6 flex justify-center items-baseline gap-2" style={{ color: scoreColor }}>
                                {Math.round(result.score)}<span className="text-4xl opacity-50">%</span>
                            </div>
                            <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
                                You need {quiz?.passing_score ?? 75}% to pass. Review the questions below and try again.
                            </p>

                            {/* Stats row */}
                            <div className="inline-flex items-center gap-6 px-8 py-4 rounded-xl border mb-10" style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border)' }}>
                                {newProfile && (
                                    <>
                                        <div className="text-left">
                                            <div className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--accent-primary)' }}>Mastery</div>
                                            <div className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>
                                                {Math.min(100, Math.round(newProfile.proficiency_level * (newProfile.proficiency_level <= 1 ? 100 : 1)))}%
                                            </div>
                                        </div>
                                        <div className="w-px h-10 bg-[var(--border)]"></div>
                                        <div className="text-left">
                                            <div className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Confidence</div>
                                            <div className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>
                                                {Math.min(100, Math.round(newProfile.confidence * 100))}%
                                            </div>
                                        </div>
                                        <div className="w-px h-10 bg-[var(--border)]"></div>
                                    </>
                                )}
                                <div className="text-left">
                                    <div className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Total XP</div>
                                    <div className="font-semibold text-lg" style={{ color: 'var(--text-primary)' }}>{result.total_xp}</div>
                                </div>
                            </div>

                            <div className="flex flex-col sm:flex-row gap-4 justify-center">
                                {retakeButton}
                                <button
                                    onClick={() => navigate(-1)}
                                    className="px-8 py-3 rounded-lg font-bold transition-colors shadow-sm"
                                    style={{ backgroundColor: 'var(--accent-primary)', color: 'white' }}
                                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#4f46e5'}
                                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'var(--accent-primary)'}
                                >
                                    Back to Course
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="space-y-4">
                        <h3 className="title-font text-xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>Question Review</h3>
                        {quiz.questions.map((q, idx) => {
                            const qId = q.id || `q${idx}`;
                            const userAns = submittedAnswers[qId];
                            const isCorrect = userAns?.trim().toLowerCase() === q.correct_answer?.trim().toLowerCase();

                            return (
                                <div key={idx} className="dark-card p-6">
                                    <div className="flex gap-4 mb-4">
                                        <div className="shrink-0 mt-1">
                                            {isCorrect ? (
                                                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-500/20 text-green-500 text-sm">✓</span>
                                            ) : (
                                                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-red-500/20 text-red-500 text-sm">✕</span>
                                            )}
                                        </div>
                                        <div>
                                            <div className="font-semibold text-lg mb-2" style={{ color: 'var(--text-primary)' }}>{q.question}</div>
                                            <div className="space-y-2 text-sm mt-4">
                                                <div className="p-3 rounded border" style={{ backgroundColor: isCorrect ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', borderColor: isCorrect ? '#22c55e' : '#ef4444' }}>
                                                    <span className="font-bold mr-2 text-xs uppercase opacity-70">Your Answer:</span>
                                                    {userAns || "Skipped"}
                                                </div>
                                                {!isCorrect && (
                                                    <div className="p-3 rounded border" style={{ backgroundColor: 'rgba(34,197,94,0.1)', borderColor: '#22c55e' }}>
                                                        <span className="font-bold mr-2 text-xs uppercase opacity-70">Correct Answer:</span>
                                                        {q.correct_answer}
                                                    </div>
                                                )}
                                                {q.explanation && (
                                                    <div className="mt-4 p-4 rounded bg-black/50 border border-[var(--border)] text-[var(--text-muted)]">
                                                        <span className="font-bold text-[var(--text-primary)] block mb-1 text-xs uppercase">Explanation</span>
                                                        {q.explanation}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        );
    }

    // --- QUIZ VIEW ---
    const currentQuestion = quiz.questions[currentQuestionIndex];
    const questionId = currentQuestion.id || `q${currentQuestionIndex}`;
    const selectedOption = answers[questionId];
    const isLastQuestion = currentQuestionIndex === quiz.questions.length - 1;

    return (
        <div className="quiz-page-root">
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
                
                .quiz-page-root {
                    --bg-primary: #0a0a0f;
                    --bg-card: #111118;
                    --bg-card-hover: #16161f;
                    --accent-primary: #6366f1;
                    --text-primary: #f1f5f9;
                    --text-muted: #64748b;
                    --border: #1e1e2e;
                    
                    background-color: var(--bg-primary);
                    color: var(--text-primary);
                    font-family: 'DM Sans', sans-serif;
                    
                    min-height: 100vh;
                    position: relative;
                }

                .quiz-bg {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.05) 0%, transparent 60%);
                    pointer-events: none;
                    z-index: 0;
                }

                .title-font {
                    font-family: 'Sora', sans-serif;
                }

                .question-card {
                    background-color: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 0.75rem;
                    padding: 2.5rem;
                    position: relative;
                    z-index: 1;
                }

                .option-row {
                    width: 100%;
                    text-align: left;
                    background-color: #16161f;
                    border: 1px solid var(--border);
                    border-radius: 0.5rem;
                    padding: 1.25rem 1.5rem;
                    color: var(--text-primary);
                    transition: all 0.15s ease;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                }

                .option-row:hover {
                    border-color: var(--accent-primary);
                    background-color: #1c1c28;
                }

                .option-row.selected {
                    border-color: var(--accent-primary);
                    background-color: rgba(99,102,241,0.15);
                    border-left: 3px solid var(--accent-primary);
                }

                .action-btn {
                    background-color: var(--accent-primary);
                    color: white;
                    font-weight: 700;
                    padding: 0.75rem 2rem;
                    border-radius: 0.5rem;
                    transition: background-color 0.15s ease;
                }
                .action-btn:hover:not(:disabled) {
                    background-color: #4f46e5;
                }
                .action-btn:disabled {
                    background-color: var(--bg-card-hover);
                    color: var(--text-muted);
                    cursor: not-allowed;
                    border: 1px solid var(--border);
                }
            `}</style>

            <div className="quiz-bg"></div>

            <div className="max-w-3xl mx-auto pt-8 px-4 relative z-10 pb-20">
                <AppBreadcrumb segments={[
                    { label: "Home", href: "/dashboard" },
                    { label: (courseId?.split(":")[0] ?? "").replace(/-/g, " ") || "Roadmap", href: `/roadmap/${courseId?.split(":")[0]}` },
                    { label: quiz.title || courseId?.replace(/-/g, " ") || "Course", href: ROUTES.COURSE(courseId!) },
                    { label: "Quiz" },
                ]} />
                <div className="flex items-end justify-between mb-2">
                    <h1 className="title-font text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                        {quiz.title || courseId?.replace(/-/g, ' ')}
                    </h1>
                    <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                        Question {currentQuestionIndex + 1} of {quiz.questions.length}
                    </div>
                </div>

                <div className="w-full h-[2px] rounded-full overflow-hidden mb-10" style={{ backgroundColor: 'var(--border)' }}>
                    <div
                        className="h-full transition-all duration-300 ease-out"
                        style={{ backgroundColor: 'var(--accent-primary)', width: `${((currentQuestionIndex + 1) / quiz.questions.length) * 100}%` }}
                    />
                </div>

                <div className="question-card">
                    <h2 className="title-font text-2xl md:text-3xl font-bold mb-10 leading-snug" style={{ color: 'var(--text-primary)' }}>
                        {currentQuestion.question}
                    </h2>

                    <div className="space-y-3">
                        {currentQuestion.options.map((option, idx) => {
                            const isSelected = selectedOption === option;
                            return (
                                <button
                                    key={idx}
                                    onClick={() => handleOptionSelect(option)}
                                    className={`option-row ${isSelected ? 'selected' : ''}`}
                                >
                                    <span className="font-medium text-lg">{option}</span>
                                </button>
                            );
                        })}
                    </div>

                    <div className="mt-12 flex justify-between items-center border-t border-[var(--border)] pt-6">
                        <button
                            onClick={() => navigate(-1)}
                            className="text-sm font-medium transition-colors"
                            style={{ color: 'var(--text-muted)' }}
                            onMouseOver={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
                            onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                        >
                            Cancel Quiz
                        </button>

                        <button
                            disabled={!selectedOption || submitting}
                            onClick={handleNext}
                            className="action-btn"
                        >
                            {submitting ? "Submitting..." : isLastQuestion ? "Submit Quiz" : "Next"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
