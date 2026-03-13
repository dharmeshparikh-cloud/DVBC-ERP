/**
 * LazyImage - Image component with lazy loading and blur-up placeholder
 * Improves page load performance by deferring off-screen images
 */

import React, { useState, useRef, useEffect, memo } from 'react';

export const LazyImage = memo(({
  src,
  alt,
  className = '',
  placeholderSrc = null,
  fallbackSrc = '/placeholder-image.png',
  width,
  height,
  objectFit = 'cover',
  onLoad,
  onError,
  ...props
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        rootMargin: '50px', // Start loading 50px before entering viewport
        threshold: 0.01
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  const handleLoad = (e) => {
    setIsLoaded(true);
    onLoad?.(e);
  };

  const handleError = (e) => {
    setHasError(true);
    onError?.(e);
  };

  const imageSrc = hasError ? fallbackSrc : (isInView ? src : placeholderSrc);

  return (
    <div
      ref={imgRef}
      className={`relative overflow-hidden ${className}`}
      style={{ width, height }}
    >
      {/* Placeholder/blur background */}
      {!isLoaded && (
        <div 
          className="absolute inset-0 bg-zinc-200 dark:bg-zinc-700 animate-pulse"
          style={{ width, height }}
        />
      )}
      
      {/* Actual image */}
      {isInView && (
        <img
          src={imageSrc}
          alt={alt}
          className={`transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
          style={{ 
            width: '100%', 
            height: '100%', 
            objectFit,
            ...props.style 
          }}
          onLoad={handleLoad}
          onError={handleError}
          loading="lazy"
          decoding="async"
          {...props}
        />
      )}
    </div>
  );
});

LazyImage.displayName = 'LazyImage';

// Avatar variant with circular shape
export const LazyAvatar = memo(({
  src,
  alt,
  size = 40,
  fallbackInitials,
  className = '',
  ...props
}) => {
  const [hasError, setHasError] = useState(false);

  if (hasError || !src) {
    // Show initials fallback
    const initials = fallbackInitials || alt?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || '?';
    return (
      <div 
        className={`flex items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-orange-600 text-white font-medium ${className}`}
        style={{ width: size, height: size, fontSize: size * 0.4 }}
      >
        {initials}
      </div>
    );
  }

  return (
    <LazyImage
      src={src}
      alt={alt}
      width={size}
      height={size}
      className={`rounded-full ${className}`}
      objectFit="cover"
      onError={() => setHasError(true)}
      {...props}
    />
  );
});

LazyAvatar.displayName = 'LazyAvatar';

// Background image variant
export const LazyBackgroundImage = memo(({
  src,
  className = '',
  children,
  overlay = false,
  ...props
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: '100px' }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (isInView && src) {
      const img = new Image();
      img.src = src;
      img.onload = () => setIsLoaded(true);
    }
  }, [isInView, src]);

  return (
    <div
      ref={containerRef}
      className={`relative ${className}`}
      style={{
        backgroundImage: isLoaded ? `url(${src})` : 'none',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        ...props.style
      }}
      {...props}
    >
      {/* Loading placeholder */}
      {!isLoaded && (
        <div className="absolute inset-0 bg-zinc-200 dark:bg-zinc-700 animate-pulse" />
      )}
      
      {/* Optional overlay */}
      {overlay && (
        <div className="absolute inset-0 bg-black/40" />
      )}
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
});

LazyBackgroundImage.displayName = 'LazyBackgroundImage';

export default LazyImage;
