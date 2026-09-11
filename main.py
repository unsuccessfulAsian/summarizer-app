import threading
import tkinter.messagebox as messagebox

import customtkinter

import storage
import summarizer
import transcript

customtkinter.set_appearance_mode("System")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Summarizer")
        self.geometry("700x500")

        storage.init_db()

        self.url_entry = customtkinter.CTkEntry(self, placeholder_text="Paste YouTube URL")
        self.url_entry.pack(fill="x", padx=10, pady=(10, 5))

        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10)

        self.summarize_button = customtkinter.CTkButton(
            button_frame, text="Summarize", command=self.on_summarize_click
        )
        self.summarize_button.pack(side="left")

        self.history_button = customtkinter.CTkButton(
            button_frame, text="History", command=self.open_history_window
        )
        self.history_button.pack(side="left", padx=(10, 0))

        self.status_label = customtkinter.CTkLabel(self, text="")
        self.status_label.pack(fill="x", padx=10)

        self.result_box = customtkinter.CTkTextbox(self, wrap="word")
        self.result_box.pack(fill="both", expand=True, padx=10, pady=10)

    def on_summarize_click(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.summarize_button.configure(state="disabled")
        self.status_label.configure(text="Working...")
        thread = threading.Thread(target=self._run_summarize, args=(url,), daemon=True)
        thread.start()

    def _run_summarize(self, url: str):
        video_id = transcript.extract_video_id(url)
        if video_id is None:
            self.after(0, self._on_error, "That doesn't look like a valid YouTube URL.")
            return

        try:
            transcript_text = transcript.fetch_transcript(video_id)
        except transcript.TranscriptError as exc:
            self.after(0, self._on_error, str(exc))
            return

        title = transcript.get_video_title(video_id)

        try:
            summary_text = summarizer.summarize(transcript_text)
        except summarizer.SummarizerError as exc:
            self.after(0, self._on_error, str(exc))
            return

        storage.save_summary(video_id, url, title, transcript_text, summary_text)
        self.after(0, self._on_success, summary_text)

    def _on_success(self, summary_text: str):
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", summary_text)
        self.status_label.configure(text="Done.")
        self.summarize_button.configure(state="normal")

    def _on_error(self, message: str):
        self.status_label.configure(text="")
        self.summarize_button.configure(state="normal")
        messagebox.showerror("Error", message)

    def open_history_window(self):
        history = storage.get_history()
        window = customtkinter.CTkToplevel(self)
        window.title("History")
        window.geometry("400x400")

        for entry in history:
            label_text = f"{entry['title']}  ({entry['created_at']})"
            row = customtkinter.CTkButton(
                window,
                text=label_text,
                anchor="w",
                command=lambda eid=entry["id"], win=window: self._load_history_item(eid, win),
            )
            row.pack(fill="x", padx=5, pady=2)

    def _load_history_item(self, summary_id: int, window):
        record = storage.get_summary(summary_id)
        if record is None:
            return
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", record["summary"])
        window.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
