import os
from dotenv import load_dotenv
from agent import ClosiraSupportAgent

load_dotenv()

def run_cli_session() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    try:
        agent = ClosiraSupportAgent(api_key=api_key)
    except FileNotFoundError:
        print("Error: The 'data/sop.json' configuration file was not found.")
        return

    print("=================================================================")
    print("✨ Closira Demo AI Agent Initialized (Bloom Aesthetics Clinic) ✨")
    print("=================================================================")
    print("Instructions: Chat naturally with the agent.")
    print("              Type 'exit', 'end', or 'quit' to close the session.\n")

    while True:
        try:
            user_input = input("Customer: ").strip()

            match user_input.lower():
                case "exit" | "end" | "quit":
                    print("\n--- Ending Session & Compiling Summary ---")
                    break
                case "":
                    print("AI Agent: I didn't quite catch that. Could you please repeat your question?")
                    continue
                case _:
                    response = agent.process_turn(user_input)
                    print(f"AI Agent: {response.reply_to_user}")
                    
                    if response.should_escalate:
                        print(f"\n🚨 [SYSTEM FLAG: HANDOFF TO HUMAN RECEPTIONIST]")
                        print(f"Reason for Escalation: {response.escalation_reason}")
                        print("-------------------------------------------------\n")
                        break
                        
        except (KeyboardInterrupt, EOFError):
            print("\n\n--- Session interrupted. Generating summary for collected data ---")
            break

    print("\n⏳ Finalizing session state and compiling structured data...")
    try:
        summary = agent.generate_session_summary()
        
        output_text = "======================= SESSION SUMMARY =======================\n"
        output_text += f"🎯 Primary Intent   : {summary.customer_intent}\n"
        output_text += f"📋 Collected Details : {summary.key_details_collected}\n"
        output_text += f"⚠️  SOP Gaps Caught  : {summary.sop_gaps_identified}\n"
        output_text += f"🚀 Next Human Action : {summary.recommended_next_action}\n"
        output_text += "===============================================================\n"
        
        print(f"\n{output_text}")
        print(" Workflow session successfully logged.")

        # AUTOMATIC FILE SAVING FOR ASSIGNMENT TRANSCRIPTS
        save_file = input("\nDo you want to save this transcript to /test_transcripts? (y/n): ").strip().lower()
        if save_file == 'y':
            filename = input("Enter filename (e.g., 1_in_sop): ").strip()
            os.makedirs("test_transcripts", exist_ok=True)
            
            if not filename.endswith('.md'):
                filename += '.md'
                
            filepath = os.path.join("test_transcripts", filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("# Conversation Transcript\n\n")
                for turn in agent.conversation_history:
                    # Gemini stores history with 'user' and 'model' roles
                    role_label = "Customer" if turn.role == "user" else "AI Agent"
                    f.write(f"**{role_label}:** {turn.parts[0].text}\n\n")
                f.write(output_text)
            print(f"Transcript saved directly to {filepath}!")

    except Exception as e:
        print(f"Failed to parse structured session summary: {e}")

if __name__ == "__main__":
    run_cli_session()