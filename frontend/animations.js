/**
 * Crimson Nyx Studios — Global Animation Engine
 *
 * Features:
 *   1. IntersectionObserver scroll reveals
 *   2. Text split character animation
 *   3. Smooth counter animation for stat numbers
 *   4. Parallax scrolling (data-parallax / data-speed)
 *   5. Magnetic button effect
 *   6. Hover tilt (3D perspective)
 *   7. Nav shrink on scroll
 *   8. Page transition overlay
 *   9. Cursor trail particles
 */

document.addEventListener('DOMContentLoaded', () => {
  const prefersReducedMotion =
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ────────────────────────────────────────────────────
  // 1. Scroll Reveal (IntersectionObserver)
  // ────────────────────────────────────────────────────
  const revealElements = document.querySelectorAll('.reveal');

  if (revealElements.length) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            revealObserver.unobserve(entry.target);
            if (!prefersReducedMotion) {
              requestAnimationFrame(() => entry.target.classList.add('active'));
            } else {
              entry.target.classList.add('active');
              entry.target.style.transition = 'none';
              entry.target.style.opacity = '1';
              entry.target.style.transform = 'none';
            }
          }
        });
      },
      { root: null, rootMargin: '0px 0px -8% 0px', threshold: 0.1 }
    );
    revealElements.forEach((el) => revealObserver.observe(el));
  }

  // ────────────────────────────────────────────────────
  // 2. Text Split Character Animation
  // ────────────────────────────────────────────────────
  const splitElements = document.querySelectorAll('[data-split]');

  splitElements.forEach((el) => {
    const text = el.textContent;
    el.textContent = '';
    el.setAttribute('aria-label', text);

    [...text].forEach((char, i) => {
      const span = document.createElement('span');
      span.className = 'split-char';
      span.textContent = char === ' ' ? '\u00A0' : char;
      span.style.transitionDelay = `${i * 40}ms`;
      el.appendChild(span);
    });

    // Observe for viewport entry
    const splitObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            splitObserver.unobserve(entry.target);
            if (prefersReducedMotion) {
              entry.target.querySelectorAll('.split-char').forEach((s) => {
                s.style.opacity = '1';
                s.style.transform = 'none';
                s.style.transition = 'none';
              });
            } else {
              entry.target
                .querySelectorAll('.split-char')
                .forEach((s) => s.classList.add('active'));
            }
          }
        });
      },
      { threshold: 0.3 }
    );
    splitObserver.observe(el);
  });

  // ────────────────────────────────────────────────────
  // 3. Counter Animation for Stats
  // ────────────────────────────────────────────────────
  const counters = document.querySelectorAll('[data-count]');

  if (counters.length) {
    const counterObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            counterObserver.unobserve(entry.target);
            animateCounter(entry.target);
          }
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach((el) => counterObserver.observe(el));
  }

  function animateCounter(el) {
    const target = parseInt(el.dataset.count, 10);
    const suffix = el.dataset.suffix || '';
    const duration = 2000;
    const start = performance.now();

    if (prefersReducedMotion || isNaN(target)) {
      el.textContent = (isNaN(target) ? el.dataset.count : target) + suffix;
      return;
    }

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * target);
      el.textContent = current + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // ────────────────────────────────────────────────────
  // 4. Parallax Scrolling
  // ────────────────────────────────────────────────────
  const parallaxElements = document.querySelectorAll('[data-parallax]');

  if (parallaxElements.length && !prefersReducedMotion) {
    let ticking = false;

    function updateParallax() {
      const scrollY = window.scrollY;
      parallaxElements.forEach((el) => {
        const speed = parseFloat(el.dataset.parallax) || 0.1;
        const offset = scrollY * speed;
        el.style.transform = `translateY(${offset}px)`;
      });
      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(updateParallax);
        ticking = true;
      }
    }, { passive: true });
  }

  // ────────────────────────────────────────────────────
  // 5. Magnetic Button Effect
  // ────────────────────────────────────────────────────
  const magneticElements = document.querySelectorAll('.magnetic');

  if (magneticElements.length && !prefersReducedMotion) {
    magneticElements.forEach((el) => {
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        el.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`;
      });

      el.addEventListener('mouseleave', () => {
        el.style.transform = 'translate(0, 0)';
      });
    });
  }

  // ────────────────────────────────────────────────────
  // 6. 3D Hover Tilt
  // ────────────────────────────────────────────────────
  const tiltElements = document.querySelectorAll('.hover-tilt');

  if (tiltElements.length && !prefersReducedMotion) {
    tiltElements.forEach((el) => {
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        el.style.transform = `perspective(600px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) scale(1.02)`;
      });

      el.addEventListener('mouseleave', () => {
        el.style.transform = 'perspective(600px) rotateY(0deg) rotateX(0deg) scale(1)';
      });
    });
  }

  // ────────────────────────────────────────────────────
  // 7. Nav Shrink on Scroll
  // ────────────────────────────────────────────────────
  const nav = document.querySelector('nav');

  if (nav && !prefersReducedMotion) {
    let navTicking = false;

    function updateNav() {
      if (window.scrollY > 80) {
        nav.classList.add('nav--scrolled');
      } else {
        nav.classList.remove('nav--scrolled');
      }
      navTicking = false;
    }

    window.addEventListener('scroll', () => {
      if (!navTicking) {
        requestAnimationFrame(updateNav);
        navTicking = true;
      }
    }, { passive: true });

    // Run immediately in case page loads scrolled down
    updateNav();
  }

  // ────────────────────────────────────────────────────
  // 8. Page Transition Overlay
  // ────────────────────────────────────────────────────
  // Create overlay element
  const overlay = document.createElement('div');
  overlay.className = 'page-transition-overlay';
  document.body.appendChild(overlay);

  // Intercept internal link clicks
  if (!prefersReducedMotion) {
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href]');
      if (!link) return;

      const href = link.getAttribute('href');
      // Skip anchors, external links, mailto, tel, javascript
      if (
        !href ||
        href.startsWith('#') ||
        href.startsWith('mailto:') ||
        href.startsWith('tel:') ||
        href.startsWith('javascript:') ||
        link.target === '_blank' ||
        link.hostname !== window.location.hostname
      ) return;

      e.preventDefault();
      overlay.classList.add('active');
      setTimeout(() => {
        window.location.href = href;
      }, 350);
    });

    // Fade in on page load
    window.addEventListener('pageshow', () => {
      overlay.classList.remove('active');
    });
  }

  // ────────────────────────────────────────────────────
  // 9. Cursor Trail Particles (opt-in areas)
  // ────────────────────────────────────────────────────
  const trailAreas = document.querySelectorAll('.cursor-trail-area');

  if (trailAreas.length && !prefersReducedMotion) {
    let lastTrailTime = 0;

    trailAreas.forEach((area) => {
      area.addEventListener('mousemove', (e) => {
        const now = Date.now();
        if (now - lastTrailTime < 50) return; // throttle
        lastTrailTime = now;

        const particle = document.createElement('div');
        particle.className = 'cursor-particle';
        particle.style.left = e.clientX - 3 + 'px';
        particle.style.top = e.clientY - 3 + 'px';
        document.body.appendChild(particle);

        setTimeout(() => particle.remove(), 800);
      });
    });
  }

  // ────────────────────────────────────────────────────
  // 10. Mobile Nav Toggle (shared across pages)
  // ────────────────────────────────────────────────────
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      navToggle.classList.toggle('active');
    });

    // Close on link click (mobile)
    navLinks.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        navToggle.classList.remove('active');
      });
    });
  }
});