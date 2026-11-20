from worker.app import ping

if __name__ == "__main__":
    job = ping.delay()
    print(f"Queued worker health task {job.id}; confirm execution in worker logs.")
