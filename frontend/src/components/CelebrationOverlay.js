import React, { useEffect, useState, useCallback } from 'react';
import confetti from 'canvas-confetti';
import { X, PartyPopper, Sparkles, Trophy } from 'lucide-react';

/**
 * CelebrationOverlay Component
 * Shows a 5-second celebration animation with confetti blasts
 * Used when sales funnel onboarding is completed (9/9 steps)
 */
const CelebrationOverlay = ({ 
  isVisible, 
  onClose, 
  userName = "Champion",
  companyName = "the client",
  projectName = ""
}) => {
  const [showContent, setShowContent] = useState(false);
  const [countdown, setCountdown] = useState(5);

  // Confetti blast function
  const fireConfetti = useCallback(() => {
    // Center burst
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    });

    // Left side burst
    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 60,
        spread: 55,
        origin: { x: 0, y: 0.6 },
        colors: ['#10b981', '#3b82f6', '#f59e0b']
      });
    }, 200);

    // Right side burst
    setTimeout(() => {
      confetti({
        particleCount: 50,
        angle: 120,
        spread: 55,
        origin: { x: 1, y: 0.6 },
        colors: ['#ef4444', '#8b5cf6', '#ec4899']
      });
    }, 400);
  }, []);

  // Continuous confetti rain
  const confettiRain = useCallback(() => {
    const duration = 5000;
    const end = Date.now() + duration;

    const frame = () => {
      confetti({
        particleCount: 3,
        angle: 60,
        spread: 55,
        origin: { x: 0, y: 0 },
        colors: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
      });
      confetti({
        particleCount: 3,
        angle: 120,
        spread: 55,
        origin: { x: 1, y: 0 },
        colors: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
      });

      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    frame();
  }, []);

  useEffect(() => {
    if (isVisible) {
      // Start animations
      setShowContent(true);
      setCountdown(5);
      
      // Fire initial confetti bursts
      fireConfetti();
      setTimeout(fireConfetti, 500);
      setTimeout(fireConfetti, 1000);
      
      // Start continuous rain
      confettiRain();

      // Countdown timer
      const countdownInterval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(countdownInterval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      // Auto close after 5 seconds
      const autoCloseTimer = setTimeout(() => {
        onClose?.();
      }, 5000);

      return () => {
        clearInterval(countdownInterval);
        clearTimeout(autoCloseTimer);
      };
    } else {
      setShowContent(false);
    }
  }, [isVisible, fireConfetti, confettiRain, onClose]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center">
      {/* Backdrop with gradient */}
      <div 
        className="absolute inset-0 bg-gradient-to-br from-emerald-900/90 via-zinc-900/95 to-blue-900/90 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-6 right-6 z-10 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors text-white"
      >
        <X className="w-6 h-6" />
      </button>

      {/* Countdown */}
      <div className="absolute top-6 left-6 z-10 text-white/60 text-sm font-mono">
        Auto-closing in {countdown}s
      </div>

      {/* Main content */}
      <div 
        className={`relative z-10 text-center px-8 py-12 max-w-2xl mx-4 transform transition-all duration-700 ${
          showContent ? 'scale-100 opacity-100' : 'scale-75 opacity-0'
        }`}
      >
        {/* Animated icons */}
        <div className="flex justify-center items-center gap-4 mb-8">
          <PartyPopper 
            className="w-12 h-12 text-yellow-400 animate-bounce" 
            style={{ animationDelay: '0ms' }}
          />
          <Trophy 
            className="w-16 h-16 text-yellow-300 animate-pulse" 
          />
          <PartyPopper 
            className="w-12 h-12 text-yellow-400 animate-bounce" 
            style={{ animationDelay: '200ms', transform: 'scaleX(-1)' }}
          />
        </div>

        {/* Sparkle decorations */}
        <div className="absolute -top-4 left-1/4 animate-ping">
          <Sparkles className="w-6 h-6 text-yellow-300" />
        </div>
        <div className="absolute -top-2 right-1/4 animate-ping" style={{ animationDelay: '300ms' }}>
          <Sparkles className="w-5 h-5 text-emerald-300" />
        </div>
        <div className="absolute top-1/3 -left-4 animate-ping" style={{ animationDelay: '600ms' }}>
          <Sparkles className="w-4 h-4 text-blue-300" />
        </div>
        <div className="absolute top-1/3 -right-4 animate-ping" style={{ animationDelay: '900ms' }}>
          <Sparkles className="w-4 h-4 text-pink-300" />
        </div>

        {/* Main celebration text */}
        <h1 className="text-5xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 via-emerald-300 to-cyan-300 mb-6 animate-pulse">
          Congratulations!
        </h1>

        {/* User message */}
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 mb-6 border border-white/20">
          <p className="text-2xl md:text-3xl text-white font-semibold leading-relaxed">
            <span className="text-yellow-300">{userName}</span>, you finally did it!
          </p>
          <p className="text-xl md:text-2xl text-emerald-300 mt-2 font-medium">
            Many more to go - Many Congratulations!
          </p>
        </div>

        {/* Project info */}
        {(companyName || projectName) && (
          <div className="text-white/80 text-lg">
            <p className="flex items-center justify-center gap-2">
              <span className="text-emerald-400">✓</span>
              <span className="font-semibold text-white">{companyName}</span> 
              <span>has been successfully onboarded!</span>
            </p>
            {projectName && (
              <p className="mt-2 text-white/60">
                Project: <span className="text-cyan-300 font-medium">{projectName}</span>
              </p>
            )}
          </div>
        )}

        {/* Animated progress bar */}
        <div className="mt-8 h-2 bg-white/20 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 rounded-full transition-all duration-[5000ms] ease-linear"
            style={{ width: showContent ? '100%' : '0%' }}
          />
        </div>

        {/* Click to continue hint */}
        <p className="mt-4 text-white/40 text-sm">
          Click anywhere or press Escape to continue
        </p>
      </div>

      {/* Floating emojis animation */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {['🎉', '🎊', '🏆', '⭐', '🌟', '💫', '🎯', '🚀'].map((emoji, i) => (
          <div
            key={i}
            className="absolute text-4xl animate-float"
            style={{
              left: `${10 + (i * 12)}%`,
              animationDelay: `${i * 0.3}s`,
              animationDuration: `${3 + (i % 3)}s`
            }}
          >
            {emoji}
          </div>
        ))}
      </div>

      {/* Custom animation styles */}
      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(100vh) rotate(0deg);
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          90% {
            opacity: 1;
          }
          100% {
            transform: translateY(-100px) rotate(360deg);
            opacity: 0;
          }
        }
        .animate-float {
          animation: float 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default CelebrationOverlay;
