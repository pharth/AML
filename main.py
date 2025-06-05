import argparse
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation.run_simulation import aml_simulation
from simulation.transaction_generator import transaction_generator
from workflows.aml_workflow import aml_workflow
from database.mongo_handler import mongo_handler

def main():
    parser = argparse.ArgumentParser(description="AML Detection System")
    parser.add_argument(
        'mode', 
        choices=['simulation', 'monitor', 'test', 'generate', 'health'],
        help='Operation mode'
    )
    parser.add_argument(
        '--duration', 
        type=int, 
        default=10,
        help='Duration in minutes for simulation mode (default: 10)'
    )
    parser.add_argument(
        '--count', 
        type=int, 
        default=20,
        help='Number of transactions to generate (default: 20)'
    )
    
    args = parser.parse_args()
    
    print("🏦 Anti-Money Laundering Detection System")
    print("="*50)
    
    try:
        if args.mode == 'simulation':
            print(f"Running full simulation for {args.duration} minutes...")
            aml_simulation.run_full_simulation(duration_minutes=args.duration)
            
        elif args.mode == 'monitor':
            print("Starting continuous monitoring...")
            aml_workflow.run_continuous(max_iterations=1000)
            
        elif args.mode == 'test':
            print("Running single test cycle...")
            aml_simulation.run_single_test()
            
        elif args.mode == 'generate':
            print(f"Generating {args.count} test transactions...")
            transaction_generator.generate_batch_transactions(args.count)
            print("✅ Transaction generation complete")
            
        elif args.mode == 'health':
            print("Checking system health...")
            health = aml_simulation.check_system_health()
            
            if all(health.values()):
                print("\n✅ All systems operational!")
                sys.exit(0)
            else:
                print("\n❌ Some systems are not operational")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            mongo_handler.close_connection()
        except:
            pass

def interactive_mode():
    """Interactive mode for easier testing"""
    print("🏦 AML Detection System - Interactive Mode")
    print("="*50)
    
    while True:
        print("\nAvailable options:")
        print("1. Check system health")
        print("2. Generate test transactions")
        print("3. Run single test")
        print("4. Run simulation (5 min)")
        print("5. Start monitoring")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        try:
            if choice == '1':
                aml_simulation.check_system_health()
                
            elif choice == '2':
                count = input("Number of transactions (default 10): ").strip()
                count = int(count) if count else 10
                transaction_generator.generate_batch_transactions(count)
                
            elif choice == '3':
                aml_simulation.run_single_test()
                
            elif choice == '4':
                aml_simulation.run_full_simulation(duration_minutes=5)
                
            elif choice == '5':
                print("Starting monitoring... (Press Ctrl+C to stop)")
                aml_workflow.run_continuous(max_iterations=1000)
                
            elif choice == '6':
                print("Goodbye! 👋")
                break
                
            else:
                print("Invalid option. Please try again.")
                
        except KeyboardInterrupt:
            print("\n⏹️  Operation interrupted")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, run interactive mode
        interactive_mode()
    else:
        # Run with command line arguments
        main()