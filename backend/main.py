import os
import json
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from graph import RedditIntelligencePipeline

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(
    title="Reddit Intelligence Engine API",
    description="A multi-agent RAG system for analyzing Reddit discussions."
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Reddit Intelligence Engine API"}

@app.get("/api/query")
def stream_query(q: str = Query(..., description="The user question to research")):
    """Streams the multi-agent execution status and final results to the client."""
    logger.info(f"Received query request: {q}")
    pipeline = RedditIntelligencePipeline(q)

    def event_generator():
        for step_update in pipeline.run():
            # Standard SSE format: "data: {JSON}\n\n"
            yield f"data: {json.dumps(step_update)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/query-sync")
def query_sync(q: str = Query(..., description="The user question to research")):
    """Synchronous version of the query endpoint. Returns the full report as JSON."""
    logger.info(f"Received sync query request: {q}")
    pipeline = RedditIntelligencePipeline(q)
    report_data = None
    for step_update in pipeline.run():
        if step_update["step"] == "completed":
            report_data = step_update["data"]
        elif step_update["step"] == "failed":
            raise HTTPException(status_code=500, detail=step_update.get("details", "Pipeline failed"))
    if report_data is None:
        raise HTTPException(status_code=500, detail="Pipeline did not produce a report")
    return report_data

@app.get("/api/reports")
def list_reports():
    """Lists summaries of all previously generated and saved reports."""
    reports = []
    if not os.path.exists(DATA_DIR):
        return reports
        
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    synthesis = data.get("synthesis", {})
                    reports.append({
                        "id": data.get("id"),
                        "query": data.get("query"),
                        "timestamp": data.get("timestamp"),
                        "confidence_score": synthesis.get("confidence_score", 0.0),
                        "consensus_summary": synthesis.get("consensus_summary", "")[:180] + "..."
                    })
            except Exception as e:
                logger.error(f"Error reading report file {filename}: {e}")
                
    # Sort by timestamp descending (newest first)
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return reports

@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    """Retrieves a single full saved report by its unique ID."""
    if not os.path.exists(DATA_DIR):
        raise HTTPException(status_code=404, detail="Reports directory not found")
        
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            # The files are named slug-uuid[:8].json
            # Or we can check inside the file
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if data.get("id") == report_id or report_id[:8] in filename:
                        return data
            except Exception as e:
                logger.error(f"Error reading report file {filename}: {e}")
                
    raise HTTPException(status_code=404, detail="Report not found")
@app.delete("/api/reports")
def clear_all_reports():
    """Deletes all saved reports from the disk."""
    try:
        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".json"):
                os.remove(os.path.join(DATA_DIR, filename))
        return {"status": "success", "message": "All reports deleted"}
    except Exception as e:
        logger.error(f"Error clearing reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/reports/{report_id}")
def delete_report(report_id: str):
    """Deletes a single report by its ID."""
    if not os.path.exists(DATA_DIR):
        raise HTTPException(status_code=404, detail="Reports directory not found")
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if data.get("id") == report_id or report_id[:8] in filename:
                        os.remove(path)
                        return {"status": "success", "message": f"Report {report_id} deleted"}
            except Exception as e:
                logger.error(f"Error reading/deleting report: {e}")
    raise HTTPException(status_code=404, detail="Report not found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
