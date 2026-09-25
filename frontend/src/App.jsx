import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const INITIAL_STATE = {
  goal: null,
  trigger: null,
  trigger_source: null,
  monitoring_location: null,
  actions: [],
  conditions: [],
  notifications: [],
  notification_channel: null,
  notification_recipient: null,
  duplicate_handling: null,
  additional_requirements: [],
  required_fields: [],
  missing_information: [],
  ambiguities: [],
  asked_questions: [],
  status: "collecting",
};

function WorkflowNode({ data }) {
  const type = data.type;

  const isCondition = type === "condition";
  const isEnd = type === "end";
  const isMerge = type === "merge";

  // ----------------------------------------------------------
  // END NODE
  // ----------------------------------------------------------

  if (isEnd) {
    return (
      <div className="flow-node end-node">
        <Handle
          type="target"
          position={Position.Top}
        />

        <div className="flow-node-number">
          {data.number}
        </div>

        <div className="flow-node-content">
          <strong>End</strong>
          <span>END</span>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------------
  // MERGE / CONTINUE NODE
  //
  // IMPORTANT:
  // Merge is not a workflow step, so it does NOT receive
  // a number.
  // ----------------------------------------------------------

  if (isMerge) {
    return (
      <div className="flow-node merge-node">
        <Handle
          type="target"
          position={Position.Top}
        />

        <div className="flow-node-content">
          <strong>Continue</strong>
          <span>MERGE</span>
        </div>

        <Handle
          type="source"
          position={Position.Bottom}
        />
      </div>
    );
  }

  // ----------------------------------------------------------
  // CONDITION NODE
  // ----------------------------------------------------------

  if (isCondition) {
    return (
      <div className="flow-node condition-node">
        <Handle
          type="target"
          position={Position.Top}
        />

        <div className="flow-node-number">
          {data.number}
        </div>

        <div className="flow-node-content">
          <strong>{data.name}</strong>
          <span>CONDITION</span>
        </div>

        <Handle
          type="source"
          position={Position.Left}
          id="yes"
          style={{ top: "70%" }}
        />

        <Handle
          type="source"
          position={Position.Right}
          id="no"
          style={{ top: "70%" }}
        />

        {/*
          YES / NO labels are intentionally NOT rendered here.

          The edge itself already displays YES / NO.
          Rendering them here as well caused duplicate labels.
        */}
      </div>
    );
  }

  // ----------------------------------------------------------
  // NORMAL NODE
  // ----------------------------------------------------------

  return (
    <div className={`flow-node ${type}-node`}>
      <Handle
        type="target"
        position={Position.Top}
      />

      <div className="flow-node-number">
        {data.number}
      </div>

      <div className="flow-node-content">
        <strong>{data.name}</strong>

        <span>
          {data.branch
            ? `${type.toUpperCase()} • ${data.branch}`
            : type.toUpperCase()}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
      />
    </div>
  );
}

const nodeTypes = {
  trigger: WorkflowNode,
  action: WorkflowNode,
  condition: WorkflowNode,
  notification: WorkflowNode,
  merge: WorkflowNode,
  end: WorkflowNode,
};

function App() {
  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! Tell me what workflow you want to create.",
    },
  ]);

  const [state, setState] = useState(INITIAL_STATE);
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ==========================================================
  // SEND MESSAGE
  // ==========================================================

  const sendMessage = async () => {
    const userMessage = message.trim();

    if (!userMessage || loading) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        role: "user",
        text: userMessage,
      },
    ]);

    setMessage("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userMessage,
            state,
          }),
        }
      );

      if (!response.ok) {
        const detail = await response.text();

        throw new Error(
          detail || `Server returned ${response.status}`
        );
      }

      const data = await response.json();

      setState(data.state);
      setWorkflow(data.workflow || null);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: data.reply,
        },
      ]);
    } catch (requestError) {
      console.error(requestError);

      setError(
        "Could not connect to the workflow server."
      );

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text:
            "I could not connect to the workflow server. Please check that the FastAPI backend is running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ==========================================================
  // RESET
  // ==========================================================

  const resetWorkflow = () => {
    setMessage("");

    setMessages([
      {
        role: "assistant",
        text: "Hi! Tell me what workflow you want to create.",
      },
    ]);

    setState(INITIAL_STATE);
    setWorkflow(null);
    setError("");
  };

  // ==========================================================
  // ENTER KEY
  // ==========================================================

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  };

  // ==========================================================
  // CREATE REACT FLOW NODES
  // ==========================================================

  const flowNodes = useMemo(() => {
    if (!workflow?.nodes) {
      return [];
    }

    /*
     * IMPORTANT:
     *
     * Merge / Continue is an internal graph node.
     * It should NOT consume a workflow step number.
     *
     * Example:
     *
     * 1 Trigger
     * 2 Condition
     * 3 YES action
     * 4 NO action
     *   Continue
     * 5 End
     */

    let stepNumber = 0;

    return workflow.nodes.map((node, index) => {
      const isMerge = node.type === "merge";

      const number = isMerge
        ? null
        : ++stepNumber;

      return {
        id: node.id,
        type: node.type,

        position:
          node.position || {
            x: 350,
            y: index * 140,
          },

        data: {
          name: node.name,
          type: node.type,
          number,
          branch: node.branch || null,
        },
      };
    });
  }, [workflow]);

  // ==========================================================
  // CREATE REACT FLOW EDGES
  // ==========================================================

  const flowEdges = useMemo(() => {
    if (!workflow?.edges) {
      return [];
    }

    return workflow.edges.map(
      (edge, index) => {
        const label = edge.label || "";

        const isBranch =
          label === "YES" ||
          label === "NO";

        return {
          id:
            edge.id ||
            `edge-${index}`,

          source: edge.source,

          target: edge.target,

          sourceHandle:
            edge.sourceHandle,

          animated: false,

          /*
           * YES / NO are shown ONLY on the
           * edges, not inside the condition node.
           */
          label:
            label || undefined,

          type: "smoothstep",

          style: {
            stroke: "#666",
            strokeWidth: 1.8,

            ...(isBranch
              ? {
                  strokeDasharray: "5 5",
                }
              : {}),
          },

          labelStyle: {
            fill: "#555",
            fontWeight: 700,
            fontSize: 11,
          },

          labelBgStyle: {
            fill: "#ffffff",
            fillOpacity: 0.9,
          },
        };
      }
    );
  }, [workflow]);

  // ==========================================================
  // UI
  // ==========================================================

  return (
    <div className="app">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="header">
        <div>
          <h1>
            Conversational Workflow Builder
          </h1>

          <p>
            Describe an automation. The
            assistant clarifies missing
            information before generating
            the workflow.
          </p>
        </div>

        <div className="header-actions">

          <div
            className={`status ${state.status}`}
          >
            {state.status === "complete"
              ? "Workflow Ready"
              : "Collecting Information"}
          </div>

          <button
            className="reset-button"
            onClick={resetWorkflow}
          >
            New Workflow
          </button>

        </div>
      </header>

      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="main">

        {/* ====================================================
            CHAT
        ==================================================== */}

        <section className="chat-panel panel">

          <div className="panel-title">

            <div>
              <h2>
                Workflow Assistant
              </h2>

              <p>
                Clarification Agent
              </p>
            </div>

            <span className="ai-badge">
              AI Agent
            </span>

          </div>

          <div className="messages">

            {messages.map(
              (msg, index) => (
                <div
                  key={`${msg.role}-${index}`}
                  className={`message ${
                    msg.role === "user"
                      ? "user-message"
                      : "assistant-message"
                  }`}
                >

                  <div className="message-label">
                    {msg.role === "user"
                      ? "You"
                      : "Assistant"}
                  </div>

                  <div className="message-bubble">
                    {msg.text}
                  </div>

                </div>
              )
            )}

            {loading && (
              <div className="message assistant-message">

                <div className="message-label">
                  Assistant
                </div>

                <div className="message-bubble thinking">
                  Thinking…
                </div>

              </div>
            )}

          </div>

          {error && (
            <div className="error-banner">
              {error}
            </div>
          )}

          <div className="input-area">

            <input
              type="text"
              placeholder="Describe the workflow you want to create…"
              value={message}
              onChange={(event) =>
                setMessage(event.target.value)
              }
              onKeyDown={handleKeyDown}
              disabled={loading}
            />

            <button
              onClick={sendMessage}
              disabled={
                loading ||
                !message.trim()
              }
            >
              {loading
                ? "Sending…"
                : "Send"}
            </button>

          </div>

        </section>

        {/* ====================================================
            COLLECTED INFORMATION
        ==================================================== */}

        <section className="state-panel panel">

          <div className="panel-title">

            <div>
              <h2>
                Collected Information
              </h2>

              <p>
                Current planning state
              </p>
            </div>

          </div>

          <div className="state-content">

            <Info
              label="Goal"
              value={state.goal}
            />

            <Info
              label="Trigger"
              value={state.trigger?.name}
            />

            <Info
              label="Trigger Source"
              value={state.trigger_source}
            />

            <Info
              label="Monitoring Location"
              value={state.monitoring_location}
            />

            <Info
              label="Actions"
              value={
                state.actions?.length || 0
              }
            />

            <Info
              label="Conditions"
              value={
                state.conditions?.length || 0
              }
            />

            <Info
              label="Notifications"
              value={
                state.notifications?.length || 0
              }
            />

            <Info
              label="Notification Channel"
              value={
                state.notification_channel
              }
            />

            <Info
              label="Notification Recipient"
              value={
                state.notification_recipient
              }
            />

            <Info
              label="Duplicate Handling"
              value={
                state.duplicate_handling
              }
            />

            <div className="info-item">

              <span>
                Missing Information
              </span>

              {state.missing_information?.length ? (
                <ul className="missing-list">

                  {state.missing_information.map(
                    (item) => (
                      <li key={item}>
                        {item.replaceAll(
                          "_",
                          " "
                        )}
                      </li>
                    )
                  )}

                </ul>
              ) : (
                <strong className="complete-text">
                  Nothing missing
                </strong>
              )}

            </div>

            {state.ambiguities?.length >
              0 && (
              <div className="info-item">

                <span>
                  Ambiguity
                </span>

                <ul className="ambiguity-list">

                  {state.ambiguities.map(
                    (item) => (
                      <li key={item}>
                        {item}
                      </li>
                    )
                  )}

                </ul>

              </div>
            )}

            {state.additional_requirements
              ?.length > 0 && (
              <div className="info-item">

                <span>
                  Additional Preferences
                </span>

                <ul>

                  {state.additional_requirements.map(
                    (item) => (
                      <li key={item}>
                        {item}
                      </li>
                    )
                  )}

                </ul>

              </div>
            )}

          </div>

        </section>

      </main>

      {/* ======================================================
          GENERATED WORKFLOW
      ====================================================== */}

      <section className="workflow-panel panel">

        <div className="panel-title">

          <div>

            <h2>
              Generated Workflow
            </h2>

            <p>
              {workflow
                ? workflow.workflow_name
                : "Generated only after clarification is complete"}
            </p>

          </div>

          {workflow && (
            <span className="ready-label">
              Ready
            </span>
          )}

        </div>

        {!workflow ? (

          <div className="empty-workflow">

            <div className="empty-icon">
              ⚡
            </div>

            <h3>
              No workflow generated yet
            </h3>

            <p>
              Answer the assistant's
              clarification questions.
              The workflow will appear
              here only when the required
              information has been
              collected.
            </p>

          </div>

        ) : (

          <div className="flow-container">

            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{
                padding: 0.2,
              }}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable
            >

              <Background
                gap={20}
                size={1}
              />

              <Controls />

              <MiniMap />

            </ReactFlow>

          </div>

        )}

      </section>

    </div>
  );
}

// ============================================================
// INFORMATION ITEM
// ============================================================

function Info({
  label,
  value,
}) {
  return (
    <div className="info-item">

      <span>
        {label}
      </span>

      <strong>
        {value === null ||
        value === undefined ||
        value === ""
          ? "Not provided"
          : value}
      </strong>

    </div>
  );
}

export default App;