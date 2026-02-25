"""
Deploy Digital Arena Enterprise to Firebase
"""

import os
import json
import subprocess
import shutil

def deploy_enterprise():
    """Deploy enterprise version to Firebase."""
    print("Digital Arena Enterprise - Firebase Deployment")
    print("=" * 60)
    
    # Check Firebase CLI
    try:
        result = subprocess.run(["firebase", "--version"], capture_output=True, text=True)
        print(f"Firebase CLI: {result.stdout.strip()}")
    except FileNotFoundError:
        print("Installing Firebase CLI...")
        subprocess.run(["npm", "install", "-g", "firebase-tools"])
    
    # Backup current config
    if os.path.exists("firebase.json"):
        shutil.copy("firebase.json", "firebase_backup.json")
        print("Backed up current firebase.json")
    
    # Use enterprise config
    if os.path.exists("firebase_enterprise.json"):
        shutil.copy("firebase_enterprise.json", "firebase.json")
        print("Using enterprise Firebase configuration")
    
    # Update to enterprise index
    if os.path.exists("firebase_public/index_enterprise.html"):
        shutil.copy("firebase_public/index_enterprise.html", "firebase_public/index.html")
        print("Updated to enterprise index.html")
    
    # Deploy
    try:
        print("Deploying to Firebase...")
        result = subprocess.run(["firebase", "deploy", "--only", "hosting"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Deployment successful!")
            print(result.stdout)
            
            # Extract URL
            for line in result.stdout.split('\n'):
                if "Hosting URL:" in line:
                    url = line.split("Hosting URL:")[1].strip()
                    print(f"Site deployed to: {url}")
            
            return True
        else:
            print(f"Deployment failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Deployment error: {e}")
        return False

if __name__ == "__main__":
    success = deploy_enterprise()
    
    if success:
        print("\n" + "=" * 60)
        print("ENTERPRISE DEPLOYMENT SUCCESSFUL!")
        print("\nFeatures Active:")
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
        print("  Health: https://digital-arena-njok.onrender.com/api/health")
    else:
        print("Deployment failed. Check logs above.")
