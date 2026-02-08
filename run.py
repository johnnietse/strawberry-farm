import argparse
import subprocess
import sys
import time
import os

def print_header():
    print(r"""
    ==================================================================
    G.O.S. (Greenhouse Operating System) | LOCAL FARM COMMAND CENTER
    ==================================================================
    Tiers: [Phytotron Fleet] [802.15.4 Mesh] [Research Backbone]
    Faculty: Dr. Majid Pahlevani & Dr. Christian Muise (Queen's)
    ==================================================================
    """)

def run_up():
    print("[SYSTEM] Launching ALL 10 G.O.S. Research Microservices...")
    try:
        # Using modern 'docker compose' (V2) for maximum compatibility
        subprocess.run(["docker", "compose", "up", "-d", "--build"], check=True)
        print("[SUCCESS] Infrastructure established.")
        print(" -> Dashboard: http://localhost:8080")
        print(" -> Backbone: PostgreSQL (Port 5432)")
        print(" -> Sync: Executing temporal curation cycles.")
    except Exception as e:
        print(f"[ERROR] Cluster failed to stabilize: {e}")

def run_down():
    print("[SYSTEM] Terminating G.O.S. Cluster and freeing resources...")
    subprocess.run(["docker", "compose", "down"])

def show_backbone_logs():
    print("[SYSTEM] Tailing Synchronization & Curation Backbone...")
    subprocess.run(["docker", "compose", "logs", "-f", "sync_engine"])

def show_ai_logs():
    print("[SYSTEM] Tailing RL-Agent & MACQ-Learner Intelligence...")
    subprocess.run(["docker", "compose", "logs", "-f", "ml_engine", "macq_learner"])

def main():
    parser = argparse.ArgumentParser(description="G.O.S. Ultimatum CLI")
    parser.add_argument("--up", action="store_true", help="Start the full 10-service cluster")
    parser.add_argument("--down", action="store_true", help="Shutdown all services")
    parser.add_argument("--logs", choices=["backbone", "ai"], help="Tail specific research logs")
    parser.add_argument("--clean", action="store_true", help="Purge research datasets and DB volumes")
    parser.add_argument("--status", action="store_true", help="Heartbeat check on all services")
    
    args = parser.parse_args()
    print_header()

    if args.up:
        run_up()
    elif args.down:
        run_down()
    elif args.logs == "backbone":
        show_backbone_logs()
    elif args.logs == "ai":
        show_ai_logs()
    elif args.status:
        subprocess.run(["docker", "compose", "ps"])
    elif args.clean:
        print("[CAUTION] Purging all research data in 3s...")
        time.sleep(3)
        subprocess.run(["docker", "compose", "down", "-v"])
        if os.path.exists("data"):
            import shutil
            shutil.rmtree("data")
        print("[CLEAN] Research workspace reset.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
