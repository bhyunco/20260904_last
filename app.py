import os
import json
import time
import queue
import threading
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

import rpa_pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(BASE_DIR, "templates")):
    alt_paths = [
        os.path.abspath(os.path.join(os.getcwd(), "최종프로젝트")),
        r"c:\Users\student\Desktop\VIBE_RPA\최종프로젝트"
    ]
    for alt in alt_paths:
        if os.path.exists(os.path.join(alt, "templates")):
            BASE_DIR = alt
            break

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "templates"), 
            static_folder=os.path.join(BASE_DIR, "static"))
app.config["SECRET_KEY"] = "vibe-rpa-secret-key-2026"

# 전역 작업 상태 관리
job_lock = threading.Lock()
is_job_running = False
job_progress = {
    "percent": 0,
    "message": "대기 중",
    "status": "idle",  # idle, running, completed, error
    "updated_at": time.time()
}

# SSE 이벤트 전달 큐 목록
client_queues = []
client_queues_lock = threading.Lock()


def broadcast_progress(percent, message, data=None, status="running"):
    global job_progress
    if percent is not None:
        job_progress["percent"] = percent
    job_progress["message"] = message
    job_progress["status"] = status
    job_progress["updated_at"] = time.time()

    payload = {
        "percent": job_progress["percent"],
        "message": message,
        "status": status,
        "timestamp": time.strftime("%H:%M:%S"),
        "data": data
    }

    with client_queues_lock:
        dead_queues = []
        for q in client_queues:
            try:
                q.put_nowait(payload)
            except Exception:
                dead_queues.append(q)
        for dq in dead_queues:
            if dq in client_queues:
                client_queues.remove(dq)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    summary = rpa_pipeline.get_dashboard_summary()
    return jsonify({
        "job": job_progress,
        "summary": summary,
        "defaults": {
            "companies": rpa_pipeline.DEFAULT_COMPANIES,
            "sender": rpa_pipeline.DEFAULT_SENDER,
            "receiver": rpa_pipeline.DEFAULT_RECEIVER,
            "app_password": rpa_pipeline.DEFAULT_APP_PASSWORD
        }
    })


@app.route("/api/stream")
def sse_stream():
    """Server-Sent Events (SSE) 엔드포인트: 실시간 % 진행률 및 로그 스트리밍"""
    def event_generator():
        q = queue.Queue(maxsize=100)
        with client_queues_lock:
            client_queues.append(q)

        # 초기 연결 시 현재 상태 전송
        initial_payload = {
            "percent": job_progress["percent"],
            "message": job_progress["message"],
            "status": job_progress["status"],
            "timestamp": time.strftime("%H:%M:%S"),
            "data": None
        }
        yield f"data: {json.dumps(initial_payload, ensure_ascii=False)}\n\n"

        try:
            while True:
                try:
                    payload = q.get(timeout=15)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # Heartbeat
                    yield f": keepalive {time.time()}\n\n"
        except GeneratorExit:
            with client_queues_lock:
                if q in client_queues:
                    client_queues.remove(q)

    return Response(event_generator(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive"
    })


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    global is_job_running
    with job_lock:
        if is_job_running:
            return jsonify({"error": "이미 실행 중인 RPA 작업이 있습니다."}), 409
        is_job_running = True

    data = request.get_json() or {}
    companies = data.get("companies") or rpa_pipeline.DEFAULT_COMPANIES
    sender = data.get("sender") or rpa_pipeline.DEFAULT_SENDER
    receiver = data.get("receiver") or rpa_pipeline.DEFAULT_RECEIVER
    app_password = data.get("app_password") or rpa_pipeline.DEFAULT_APP_PASSWORD
    headless = data.get("headless", True)

    def worker():
        global is_job_running
        try:
            broadcast_progress(0, "RPA 자동화 작업 시작 중...", status="running")

            def progress_cb(percent, msg, summary_data=None):
                st = "completed" if percent == 100 else "running"
                broadcast_progress(percent, msg, data=summary_data, status=st)

            rpa_pipeline.run_full_rpa_pipeline(
                companies=companies,
                sender=sender,
                receiver=receiver,
                app_password=app_password,
                headless=headless,
                progress_callback=progress_cb
            )
        except Exception as e:
            broadcast_progress(None, f"치명적 오류 발생: {str(e)}", status="error")
        finally:
            with job_lock:
                is_job_running = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    return jsonify({"success": True, "message": "RPA 파이프라인이 백그라운드에서 실행되었습니다."})


@app.route("/api/send-email", methods=["POST"])
def trigger_send_email():
    """현재 생성되어 있는 DE.xlsx를 기반으로 비즈니스 이메일만 즉시 전송"""
    data = request.get_json() or {}
    sender = data.get("sender") or rpa_pipeline.DEFAULT_SENDER
    receiver = data.get("receiver") or rpa_pipeline.DEFAULT_RECEIVER
    app_password = data.get("app_password") or rpa_pipeline.DEFAULT_APP_PASSWORD
    subject = data.get("subject") or "교육회사별 시장반응결과물 전송드립니다."

    if not os.path.exists(rpa_pipeline.FILE_DE):
        return jsonify({"error": "전송할 DE.xlsx 파일이 존재하지 않습니다. 먼저 RPA를 실행해주세요."}), 400

    logs = []
    try:
        rpa_pipeline.send_email(
            sender=sender,
            receiver=receiver,
            app_password=app_password,
            subject=subject,
            attachment_path=rpa_pipeline.FILE_DE,
            log_callback=lambda m: logs.append(m)
        )
        return jsonify({
            "success": True,
            "message": f"'{receiver}'로 비즈니스 보고서 이메일이 성공적으로 전송되었습니다!",
            "logs": logs
        })
    except Exception as e:
        return jsonify({"error": f"이메일 전송 중 오류 발생: {str(e)}", "logs": logs}), 500


@app.route("/api/sync-supabase", methods=["POST"])
def sync_supabase_endpoint():
    summary = rpa_pipeline.get_dashboard_summary()
    ok = rpa_pipeline.sync_to_supabase(summary)
    if ok:
        return jsonify({"success": True, "message": "Supabase 클라우드 동기화 완료!"})
    return jsonify({"error": "Supabase 동기화 실패. 환경 변수를 확인하세요."}), 500


@app.route("/api/download/<filename>", methods=["GET"])
def download_file(filename):
    allowed_files = {
        "DE.xlsx": rpa_pipeline.FILE_DE,
        "naver_cafe_article_yn.xlsx": rpa_pipeline.FILE_YN,
        "naver_cafe_article.xlsx": rpa_pipeline.FILE_RAW
    }
    if filename not in allowed_files:
        return jsonify({"error": "유효하지 않은 파일명입니다."}), 404

    target_file = allowed_files[filename]
    if not os.path.exists(target_file):
        # 서버리스 환경(Vercel)에서는 Supabase 데이터를 기반으로 엑셀 즉석 스트리밍
        try:
            import io
            from flask import send_file
            summary = rpa_pipeline.get_dashboard_summary()
            if summary and summary.get("has_data"):
                buf = io.BytesIO()
                if filename == "DE.xlsx":
                    df_out = pd.DataFrame(summary.get("table_data", []))
                    df_out.to_excel(buf, index=False)
                else:
                    df_out = pd.DataFrame(summary.get("articles", []))
                    df_out.to_excel(buf, index=False)
                buf.seek(0)
                return send_file(
                    buf,
                    as_attachment=True,
                    download_name=filename,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            print(f"엑셀 동적 생성 오류: {e}")
        return jsonify({"error": "파일이 아직 생성되지 않았습니다."}), 404

    return send_from_directory(
        directory=os.path.dirname(target_file),
        path=os.path.basename(target_file),
        as_attachment=True
    )


if __name__ == "__main__":
    print("=" * 60)
    print("VIBE RPA Flask 대시보드 서버 시작 (포트 5000)")
    print("브라우저에서 http://127.0.0.1:5000 으로 접속하세요.")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
