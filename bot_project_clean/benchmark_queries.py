"""
Performance Benchmark Script

Measures query performance before and after optimization.
Helps validate that database indexes are improving performance.

Usage:
    # Create baseline before fixes
    python benchmark_queries.py --baseline
    
    # Compare after fixes
    python benchmark_queries.py --compare
    
    # Run specific benchmark
    python benchmark_queries.py --test availability
"""

import asyncio
import time
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select, and_
from database import async_session_factory
from models import Booking, Club, Computer, User

BENCHMARK_FILE = "benchmark_results.json"


class QueryBenchmark:
    """Benchmark runner for database queries."""
    
    def __init__(self):
        self.results = {}
    
    async def benchmark_availability_query(self, iterations=100):
        """Benchmark the availability check query."""
        print(f"\nBenchmarking availability query ({iterations} iterations)...")
        
        times = []
        
        async with async_session_factory() as session:
            # Get a real club and computer for testing
            club = await session.get(Club, 1)
            if not club:
                print("⚠️  No club found, skipping test")
                return None
            
            result = await session.execute(
                select(Computer).where(Computer.club_id == club.id).limit(1)
            )
            computer = result.scalars().first()
            
            if not computer:
                print("⚠️  No computer found, skipping test")
                return None
            
            # Run benchmark
            for i in range(iterations):
                start_time = time.time()
                
                # This is the critical query from handlers/api.py
                result = await session.execute(
                    select(Booking).where(
                        and_(
                            Booking.club_id == club.id,
                            Booking.computer_name == computer.name,
                            Booking.status == "CONFIRMED"
                        )
                    )
                )
                bookings = result.scalars().all()
                
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                times.append(elapsed)
                
                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i + 1}/{iterations}")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        
        return {
            "avg": avg_time,
            "min": min_time,
            "max": max_time,
            "p95": p95_time,
            "iterations": iterations
        }
    
    async def benchmark_user_bookings_query(self, iterations=100):
        """Benchmark the user bookings list query."""
        print(f"\nBenchmarking user bookings query ({iterations} iterations)...")
        
        times = []
        
        async with async_session_factory() as session:
            # Get a real user for testing
            result = await session.execute(select(User).limit(1))
            user = result.scalars().first()
            
            if not user:
                print("⚠️  No user found, skipping test")
                return None
            
            # Run benchmark
            for i in range(iterations):
                start_time = time.time()
                
                # This is the query from handlers/clubs.py
                result = await session.execute(
                    select(Booking)
                    .where(Booking.user_id == user.id)
                    .order_by(Booking.start_time.desc())
                )
                bookings = result.scalars().all()
                
                # Simulate N+1 problem (loading clubs)
                for booking in bookings:
                    club = await session.get(Club, booking.club_id)
                
                elapsed = (time.time() - start_time) * 1000
                times.append(elapsed)
                
                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i + 1}/{iterations}")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        
        return {
            "avg": avg_time,
            "min": min_time,
            "max": max_time,
            "p95": p95_time,
            "iterations": iterations
        }
    
    async def benchmark_club_computers_query(self, iterations=100):
        """Benchmark loading computers for a club."""
        print(f"\nBenchmarking club computers query ({iterations} iterations)...")
        
        times = []
        
        async with async_session_factory() as session:
            club = await session.get(Club, 1)
            if not club:
                print("⚠️  No club found, skipping test")
                return None
            
            for i in range(iterations):
                start_time = time.time()
                
                result = await session.execute(
                    select(Computer).where(
                        and_(
                            Computer.club_id == club.id,
                            Computer.is_active == True
                        )
                    )
                )
                computers = result.scalars().all()
                
                elapsed = (time.time() - start_time) * 1000
                times.append(elapsed)
                
                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i + 1}/{iterations}")
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]
        
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        
        return {
            "avg": avg_time,
            "min": min_time,
            "max": max_time,
            "p95": p95_time,
            "iterations": iterations
        }
    
    async def run_all_benchmarks(self):
        """Run all benchmarks."""
        print("=" * 60)
        print("PERFORMANCE BENCHMARK")
        print("=" * 60)
        print(f"Started at: {datetime.now()}")
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Test 1: Availability query
        result = await self.benchmark_availability_query()
        if result:
            self.results["tests"]["availability_query"] = result
        
        # Test 2: User bookings query
        result = await self.benchmark_user_bookings_query()
        if result:
            self.results["tests"]["user_bookings_query"] = result
        
        # Test 3: Club computers query
        result = await self.benchmark_club_computers_query()
        if result:
            self.results["tests"]["club_computers_query"] = result
        
        print("\n" + "=" * 60)
        print("BENCHMARK COMPLETE")
        print("=" * 60)
        
        return self.results
    
    def save_results(self, label="baseline"):
        """Save benchmark results to file."""
        filepath = Path(BENCHMARK_FILE)
        
        # Load existing results
        if filepath.exists():
            with open(filepath, 'r') as f:
                all_results = json.load(f)
        else:
            all_results = {}
        
        # Add new results
        all_results[label] = self.results
        
        # Save
        with open(filepath, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\nResults saved to {filepath} under label '{label}'")
    
    @staticmethod
    def compare_results():
        """Compare baseline vs current results."""
        filepath = Path(BENCHMARK_FILE)
        
        if not filepath.exists():
            print("❌ No benchmark results found. Run --baseline first.")
            return
        
        with open(filepath, 'r') as f:
            all_results = json.load(f)
        
        if "baseline" not in all_results:
            print("❌ No baseline results found. Run --baseline first.")
            return
        
        if "optimized" not in all_results:
            print("❌ No optimized results found. Run --compare first.")
            return
        
        baseline = all_results["baseline"]["tests"]
        optimized = all_results["optimized"]["tests"]
        
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)
        
        for test_name in baseline.keys():
            if test_name not in optimized:
                continue
            
            base_avg = baseline[test_name]["avg"]
            opt_avg = optimized[test_name]["avg"]
            improvement = ((base_avg - opt_avg) / base_avg) * 100
            speedup = base_avg / opt_avg if opt_avg > 0 else 0
            
            print(f"\n{test_name.replace('_', ' ').title()}")
            print(f"  Baseline:  {base_avg:.2f}ms")
            print(f"  Optimized: {opt_avg:.2f}ms")
            
            if improvement > 0:
                print(f"  Improvement: {improvement:.1f}% faster ({speedup:.1f}x speedup)")
            else:
                print(f"  Regression: {abs(improvement):.1f}% slower")
        
        print("\n" + "=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Benchmark database queries")
    parser.add_argument("--baseline", action="store_true", help="Create baseline benchmark")
    parser.add_argument("--compare", action="store_true", help="Compare against baseline")
    parser.add_argument("--test", choices=["availability", "user_bookings", "club_computers"], 
                       help="Run specific test only")
    
    args = parser.parse_args()
    
    benchmark = QueryBenchmark()
    
    if args.baseline:
        print("Creating baseline benchmark...")
        await benchmark.run_all_benchmarks()
        benchmark.save_results("baseline")
    
    elif args.compare:
        print("Running optimized benchmark...")
        await benchmark.run_all_benchmarks()
        benchmark.save_results("optimized")
        
        print("\n")
        QueryBenchmark.compare_results()
    
    elif args.test:
        if args.test == "availability":
            await benchmark.benchmark_availability_query()
        elif args.test == "user_bookings":
            await benchmark.benchmark_user_bookings_query()
        elif args.test == "club_computers":
            await benchmark.benchmark_club_computers_query()
    
    else:
        # Default: run all benchmarks
        await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    print("=" * 60)
    print("Performance Benchmark Tool")
    print("=" * 60)
    print("")
    print("This tool measures query performance to validate optimizations.")
    print("")
    print("Workflow:")
    print("1. Run --baseline BEFORE adding indexes")
    print("2. Add indexes with migrate_add_indexes.py")
    print("3. Run --compare to see improvements")
    print("")
    
    asyncio.run(main())

