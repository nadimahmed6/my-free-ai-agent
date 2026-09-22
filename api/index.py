import os
import json
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai
from supabase import create_client, Client

# ১. এনভায়রনমেন্ট ভেরিয়েবল থেকে চাবি সংগ্রহ
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Gemini এবং Supabase কনফিগারেশন
genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_agent_cycle():
    try:
        # ২. Supabase থেকে পেন্ডিং টাস্ক খোঁজ করা
        response = supabase.table("tasks").select("*").eq("status", "pending").limit(1).execute()
        tasks = response.data

        if not tasks:
            # কোনো কাজ না থাকলে ব্যাকগ্রাউন্ডে সেভ রেখে বন্ধ হবে
            return "No pending tasks found."

        current_task = tasks[0]
        task_id = current_task["id"]
        task_desc = current_task["task_description"]

        # ৩. Gemini AI-এর মাধ্যমে সিদ্ধান্ত ও কাজ সম্পন্ন করা
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        system_prompt = f"""
        তুমি একটি স্বাধীন স্বায়ত্তশাসিত এআই এজেন্ট (Autonomous AI Agent)। 
        তোমার বর্তমান কাজ হলো: "{task_desc}"।
        
        সুস্পষ্ট এবং কাজের উপযোগী উত্তর প্রদান করো।
        """
        
        ai_response = model.generate_content(system_prompt)
        result_text = ai_response.text

        # ৪. কাজের স্ট্যাটাস 'completed' এ আপডেট করা
        supabase.table("tasks").update({"status": "completed"}).eq("id", task_id).execute()

        # ৫. কাজের ফলাফল logs টেবিলে জমা রাখা
        supabase.table("logs").insert({
            "action": f"Executed Task #{task_id}: {task_desc}",
            "result": result_text
        }).execute()

        return f"Successfully processed task ID {task_id}"

    except Exception as e:
        return f"Error executing agent: {str(e)}"

# Vercel Serverless Function Handler
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        output = run_agent_cycle()
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(output.encode('utf-8'))
        return
  
