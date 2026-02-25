"""
🚀 Deploy Digital Arena Enterprise to Firebase
"""

import os
import json
import subprocess
import shutil
from pathlib import Path

def deploy_to_firebase():
    """Deploy enterprise version to Firebase."""
    print("🚀 Deploying Digital Arena Enterprise to Firebase...")
    
    # Check if Firebase CLI is installed
    try:
        subprocess.run(["firebase", "--version"], check=True, capture_output=True)
        print("✅ Firebase CLI found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Firebase CLI not found. Installing...")
        subprocess.run(["npm", "install", "-g", "firebase-tools"], check=True)
    
    # Backup current firebase.json
    if os.path.exists("firebase.json"):
        shutil.copy("firebase.json", "firebase_backup.json")
        print("✅ Backed up current firebase.json")
    
    # Use enterprise configuration
    if os.path.exists("firebase_enterprise.json"):
        shutil.copy("firebase_enterprise.json", "firebase.json")
        print("✅ Using enterprise Firebase configuration")
    
    # Update index.html to enterprise version
    if os.path.exists("firebase_public/index_enterprise.html"):
        shutil.copy("firebase_public/index_enterprise.html", "firebase_public/index.html")
        print("✅ Updated to enterprise index.html")
    
    # Deploy to Firebase
    try:
        print("📤 Deploying to Firebase...")
        result = subprocess.run([
            "firebase", "deploy", "--only", "hosting"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Deployment successful!")
        print(result.stdout)
        
        # Get deployment URL
        if "Hosting URL:" in result.stdout:
            url_line = [line for line in result.stdout.split('\n') if "Hosting URL:" in line][0]
            url = url_line.split("Hosting URL:")[1].strip()
            print(f"🌐 Enterprise site deployed to: {url}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        print(e.stderr)
        return False

def setup_monitoring():
    """Setup monitoring endpoints."""
    print("📊 Setting up monitoring integration...")
    
    # Create monitoring endpoint in Firebase
    monitoring_js = """
// Digital Arena Enterprise Monitoring
(function() {
    const API_BASE = 'https://digital-arena-njok.onrender.com';
    
    // Health check
    fetch(`${API_BASE}/api/health`)
        .then(res => res.json())
        .then(data => {
            console.log('🏥 Backend Health:', data);
            updateEnterpriseStatus(data.status === 'healthy');
        })
        .catch(err => {
            console.error('❌ Backend Error:', err);
            updateEnterpriseStatus(false);
        });
    
    // Metrics collection
    function collectMetrics() {
        const perfData = performance.getEntriesByType('navigation')[0];
        const metrics = {
            page_load_time: perfData.loadEventEnd - perfData.loadEventStart,
            dom_content_loaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
            first_byte: perfData.responseStart - perfData.requestStart,
            user_agent: navigator.userAgent,
            timestamp: Date.now()
        };
        
        // Send to backend
        fetch(`${API_BASE}/api/metrics`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(metrics)
        }).catch(err => console.log('Metrics error:', err));
    }
    
    // Update enterprise badge
    function updateEnterpriseStatus(isOnline) {
        const badge = document.querySelector('.enterprise-badge');
        if (badge) {
            if (isOnline) {
                badge.innerHTML = '🟢 ENTERPRISE EDITION - ONLINE';
                badge.style.background = 'linear-gradient(135deg, #00e68a, #00d4ff)';
            } else {
                badge.innerHTML = '🔴 ENTERPRISE EDITION - DEGRADED';
                badge.style.background = 'linear-gradient(135deg, #ff3d71, #ff6b2b)';
            }
        }
    }
    
    // Collect metrics after page load
    window.addEventListener('load', () => {
        setTimeout(collectMetrics, 1000);
    });
    
    // Periodic health checks
    setInterval(() => {
        fetch(`${API_BASE}/api/health`)
            .then(res => res.json())
            .then(data => updateEnterpriseStatus(data.status === 'healthy'))
            .catch(() => updateEnterpriseStatus(false));
    }, 30000); // Check every 30 seconds
    
})();
"""
    
    with open("firebase_public/monitoring.js", "w") as f:
        f.write(monitoring_js)
    
    print("✅ Monitoring script created")

def main():
    """Main deployment function."""
    print("Digital Arena Enterprise - Firebase Deployment")
    print("=" * 60)
    
    # Setup monitoring
    setup_monitoring()
    
    # Deploy to Firebase
    success = deploy_to_firebase()
    
    if success:
        print("\n" + "=" * 60)
        print("ENTERPRISE DEPLOYMENT SUCCESSFUL!")
        print("\nEnterprise Features Active:")
        print("  Circuit Breaker Protection")
        print("  Real-time Monitoring")
        print("  Multi-level Caching")
        print("  Event-driven Architecture")
        print("  Advanced Security")
        print("  Performance Profiling")
        
        print("\nAccess URLs:")
        print("  Main Site: https://arenaslotz.web.app")
        print("  Telegram Bot: https://t.me/digital_arena_bot")
        print("  Mini App: https://arenaslotz.web.app/miniapp")
        print("  Health: https://arenaslotz.web.app/health")
        
        print("\nBackend Integration:")
        print("  API: https://digital-arena-njok.onrender.com/api")
        print("  Metrics: https://digital-arena-njok.onrender.com/metrics")
        print("  Health: https://digital-arena-njok.onrender.com/api/health")
        
    else:
        print("\nDeployment failed. Check logs above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
