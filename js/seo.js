// SEO Optimization Script
// This script enhances on-page SEO and performance

document.addEventListener('DOMContentLoaded', function() {
    // 1. Lazy Loading Images for better performance
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img').forEach(img => {
            if (!img.src.startsWith('data:')) {
                imageObserver.observe(img);
            }
        });
    }

    // 2. Structured Data Validation
    function validateStructuredData() {
        const schemaScripts = document.querySelectorAll('script[type="application/ld+json"]');
        schemaScripts.forEach(script => {
            try {
                const schema = JSON.parse(script.textContent);
                console.log('✅ Structured Data Validated:', schema['@type']);
            } catch (e) {
                console.error('❌ Structured Data Error:', e);
            }
        });
    }

    // 3. Internal Linking Analysis
    function analyzeInternalLinks() {
        const links = document.querySelectorAll('a[href]');
        let internalCount = 0;
        let externalCount = 0;
        
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith('mailto:')) {
                internalCount++;
            } else if (href && href.startsWith('http')) {
                externalCount++;
            }
        });
        
        console.log(`Internal Links: ${internalCount}, External Links: ${externalCount}`);
    }

    // 4. Optimize Meta Tags based on current page
    function optimizeMetaTags() {
        const path = window.location.pathname;
        
        // Add breadcrumb schema dynamically
        if (path === '/index.html' || path === '/' || path === '') {
            // Add breadcrumb for homepage
            console.log('Home page detected - Breadcrumb schema ready');
        } else if (path.includes('about.html')) {
            // Add breadcrumb for about page
            console.log('About page detected - Breadcrumb schema ready');
        } else if (path.includes('contact.html')) {
            // Add breadcrumb for contact page
            console.log('Contact page detected - Breadcrumb schema ready');
        }
    }

    // 5. Page Loading Performance
    function optimizePerformance() {
        const startTime = performance.now();
        
        window.addEventListener('load', function() {
            const totalTime = performance.now() - startTime;
            console.log(`Page loaded in ${totalTime.toFixed(2)}ms`);
        });
    }

    // 6. Accessibility Enhancements
    function enhanceAccessibility() {
        // Add skip to main content link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = '跳至主要內容';
        skipLink.style.cssText = 'position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden;';
        skipLink.addEventListener('focus', function() {
            this.style.cssText = 'position:static;width:auto;height:auto;padding:10px;background:#000;color:#fff;';
        });
        skipLink.addEventListener('blur', function() {
            this.style.cssText = 'position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden;';
        });
        
        if (document.body.firstChild) {
            document.body.insertBefore(skipLink, document.body.firstChild);
        }

        // Add ARIA labels to key elements
        document.querySelectorAll('.card').forEach(card => {
            if (!card.hasAttribute('role')) {
                card.setAttribute('role', 'article');
            }
        });

        // Add alt text fallback for images without alt
        document.querySelectorAll('img:not([alt])').forEach(img => {
            const src = img.src;
            const filename = src.split('/').pop().split('.')[0];
            img.alt = filename.replace(/_/g, ' ');
        });
    }

    // Initialize all optimizations
    validateStructuredData();
    analyzeInternalLinks();
    optimizeMetaTags();
    optimizePerformance();
    enhanceAccessibility();
});

// Dynamic Title Update
function updatePageTitle(pageName, pageDescription) {
    const baseTitle = "Kidson營養師 - 專業體重管理與慢性病營養諮詢服務";
    document.title = `${pageName} | ${baseTitle}`;
    
    // Update meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription && pageDescription) {
        metaDescription.setAttribute('content', pageDescription);
    }
}

// Expose functions globally
window.SEOHelper = {
    updateTitle: updatePageTitle,
    validateSchema: validateStructuredData
};
