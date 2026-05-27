import { useState } from "react";

function App() {
  const [tab, setTab] = useState("text");
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);
  const [response, setResponse] = useState("");

  // TEXT REQUEST
  const sendText = async () => {
    try {
      const formData = new FormData();
      formData.append("prompt", prompt);

      const res = await fetch("http://127.0.0.1:8000/text", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      setResponse(data.response);
    } catch (error) {
      setResponse("Error in text request");
      console.error(error);
    }
  };

  // IMAGE / AUDIO / VIDEO REQUEST
  const uploadFile = async () => {
    try {
      if (!file) {
        alert("Choose a file first");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`http://127.0.0.1:8000/${tab}`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      setResponse(data.response);

      // reset file after upload
    } catch (error) {
      setResponse(`Error uploading ${tab}`);
      console.error(error);
    }
  };

  return (
    <div
      style={{
        background: "#0f1220",
        minHeight: "100vh",
        color: "white",
        textAlign: "center",
        padding: "40px",
      }}
    >
      <h1>TIAV Multimodal Demo</h1>

      <div style={{ marginBottom: "30px" }}>
        <button onClick={() => setTab("text")}>Text</button>
        <button onClick={() => setTab("image")}>Image</button>
        <button onClick={() => setTab("audio")}>Audio</button>
        <button onClick={() => setTab("video")}>Video</button>
      </div>

      {tab === "text" ? (
        <div>
          <h2>Text Input</h2>

          <textarea
            rows="5"
            cols="60"
            placeholder="Type prompt here..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />

          <br />
          <br />

          <button onClick={sendText}>
            Send to Model
          </button>
        </div>
      ) : (
        <div>
          <h2>{tab.toUpperCase()} Upload</h2>

          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
          />

          <br />
          <br />

          <button onClick={uploadFile}>
            Upload {tab}
          </button>
        </div>
      )}

      <div style={{ marginTop: "40px" }}>
        <h2>Response:</h2>
        <p>{response}</p>
      </div>
    </div>
  );
}

export default App;