import "./App.css";
import { useState, useEffect } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useTracks,
  VideoTrack,
  useLocalParticipant,
  useRoomContext,
  useParticipants
} from "@livekit/components-react";
import { Track } from "livekit-client";
import "@livekit/components-styles";

/* ================= FETCH TOKEN FROM BACKEND (JWT BASED) ================= */
async function fetchToken(room) {
  const access = localStorage.getItem("access");

  if (!access) {
    throw new Error("Not authenticated");
  }

  const res = await fetch("http://127.0.0.1:8000/api/live/token/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${access}`,
    },
    body: JSON.stringify({ room }),
  });

  if (!res.ok) throw new Error("Failed to fetch LiveKit token");
  return res.json();
}

/* ================= PARTICIPANTS ================= */
function ParticipantsPanel() {
  const participants = useParticipants();
  const room = useRoomContext();
  const [open, setOpen] = useState(true);
  const [showOverlay, setShowOverlay] = useState(false);
  const [raisedHands, setRaisedHands] = useState({});

  useEffect(() => {
    const handleData = (payload) => {
      const text = new TextDecoder().decode(payload);
      try {
        const msg = JSON.parse(text);
        if (msg.type === "raise-hand") {
          setRaisedHands((prev) => ({ ...prev, [msg.user]: true }));
          setTimeout(() => {
            setRaisedHands((prev) => {
              const updated = { ...prev };
              delete updated[msg.user];
              return updated;
            });
          }, 15000);
        }
      } catch {}
    };

    room.on("dataReceived", handleData);
    return () => room.off("dataReceived", handleData);
  }, [room]);

  const visibleParticipants = participants.slice(0, 4);
  const remainingCount = participants.length - 4;

  return (
    <div className="participants-wrapper">
      <div className="participants-header" onClick={() => setOpen(!open)}>
        <span>Participants</span>
        <span>{open ? "▾" : "▸"}</span>
      </div>

      {open && (
        <div className="participants-row">
          {visibleParticipants.map((p) => (
            <div key={p.identity} className="participant-card">
              <div className="participant-avatar">
                {p.identity.charAt(0).toUpperCase()}
              </div>
              <div className="participant-name">
                {p.identity} {raisedHands[p.identity] && "✋"}
              </div>
            </div>
          ))}

          {remainingCount > 0 && (
            <div
              className="participant-card participant-more-card"
              onClick={() => setShowOverlay(true)}
            >
              <div className="participant-more">+{remainingCount}</div>
              <div className="participant-name">more</div>
            </div>
          )}
        </div>
      )}

      {showOverlay && (
        <div className="participants-overlay">
          <div className="participants-overlay-header">
            <span>All Participants</span>
            <button onClick={() => setShowOverlay(false)}>✕</button>
          </div>

          <div className="participants-overlay-list">
            {participants.map((p) => (
              <div key={p.identity} className="participant-card overlay-card">
                <div className="participant-avatar">
                  {p.identity.charAt(0).toUpperCase()}
                </div>
                <div className="participant-name">
                  {p.identity} {raisedHands[p.identity] && "✋"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ================= CHAT ================= */
function ChatPanel({ role }) {
  const { localParticipant } = useLocalParticipant();
  const room = useRoomContext();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    const handleData = (payload, participant) => {
      const text = new TextDecoder().decode(payload);
      try {
        const msg = JSON.parse(text);
        if (msg.type === "raise-hand") return;
      } catch {}
      setMessages((prev) => [...prev, { sender: participant.identity, text }]);
    };

    room.on("dataReceived", handleData);
    return () => room.off("dataReceived", handleData);
  }, [room]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const encoder = new TextEncoder();
    await localParticipant.publishData(encoder.encode(input), { reliable: true });
    setMessages((prev) => [...prev, { sender: localParticipant.identity, text: input }]);
    setInput("");
  };

  const raiseHand = async () => {
    const message = { type: "raise-hand", user: localParticipant.identity };
    const encoder = new TextEncoder();
    await localParticipant.publishData(
      encoder.encode(JSON.stringify(message)),
      { reliable: true }
    );
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((msg, i) => {
          const isMe = msg.sender === localParticipant.identity;
          const isTeacher = msg.sender.toLowerCase().includes("teacher");

          return (
            <div key={i} className={`chat-row ${isMe ? "me" : "other"}`}>
              <div
                className={`chat-bubble 
                  ${isMe ? "my-message" : ""}
                  ${!isMe && isTeacher ? "teacher-message" : ""}
                  ${!isMe && !isTeacher ? "student-message" : ""}
                `}
              >
                {!isMe && <div className="chat-name">{msg.sender}</div>}
                <div>{msg.text}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="chat-input-area">
        {role === "student" && (
          <button onClick={raiseHand} className="raise-hand-btn">✋</button>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Your message here"
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>➤</button>
      </div>
    </div>
  );
}

/* ================= CLASSROOM ================= */
function ClassroomUI({ isRecording, role }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const tracks = useTracks([
    { source: Track.Source.Camera },
    { source: Track.Source.ScreenShare },
  ]);

  const teacherTrack = tracks.find(
    (t) => t.participant.identity.toLowerCase().includes("teacher")
  );

  if (!teacherTrack) {
    return (
      <div className="waiting-screen">
        <h2>Waiting for teacher to start video or share screen…</h2>
      </div>
    );
  }

  return (
    <div className="classroom-layout">
      <div className={`main-stage ${sidebarOpen ? "" : "full-width"}`}>
        <button
          className="toggle-sidebar-btn"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? "Hide Chat" : "Show Chat"}
        </button>

        {isRecording && <div className="recording-badge">🔴 Recording</div>}
        <VideoTrack trackRef={teacherTrack} />
      </div>

      {sidebarOpen && (
        <div className="right-sidebar">
          <ParticipantsPanel />
          <ChatPanel role={role} />
        </div>
      )}
    </div>
  );
}

/* ================= CONTROLS ================= */
function TeacherControls({ isRecording, setIsRecording }) {
  const { localParticipant } = useLocalParticipant();
  const room = useRoomContext();

  return (
    <div className="control-bar">
      <button onClick={() => localParticipant.setMicrophoneEnabled(!localParticipant.isMicrophoneEnabled)}>Mic</button>
      <button onClick={() => localParticipant.setCameraEnabled(!localParticipant.isCameraEnabled)}>Camera</button>
      <button onClick={() => localParticipant.setScreenShareEnabled(true)}>Share Screen</button>
      <button onClick={() => setIsRecording(!isRecording)}>
        {isRecording ? "Stop Recording" : "Start Recording"}
      </button>
      <button onClick={() => window.confirm("Leave class?") && room.disconnect()}>
        Leave
      </button>
    </div>
  );
}

function StudentControls() {
  const room = useRoomContext();
  return (
    <div className="control-bar">
      <button onClick={() => window.confirm("Leave class?") && room.disconnect()}>
        Leave Class
      </button>
    </div>
  );
}

/* ================= MAIN APP ================= */
export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [data, setData] = useState(null);
  const [role, setRole] = useState(null);

  const joinClass = async () => {
    try {
      const info = await fetchToken("testroom");
      setRole(info.is_teacher ? "teacher" : "student");
      setData(info);
    } catch (err) {
      alert("You must be logged in to join this class.");
      console.error(err);
    }
  };

  if (!data) {
    return (
      <div style={{ padding: 20 }}>
        <h2>LiveKit Classroom</h2>
        <button onClick={joinClass}>Enter Classroom</button>
      </div>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={data.livekit_url}
      token={data.token}
      connect={true}
      video={role === "teacher"}
      audio={true}
    >
      <ClassroomUI isRecording={isRecording} role={role} />
      {role === "teacher" && (
        <TeacherControls
          isRecording={isRecording}
          setIsRecording={setIsRecording}
        />
      )}
      {role === "student" && <StudentControls />}
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}
