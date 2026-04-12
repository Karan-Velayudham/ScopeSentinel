import AgentChatWorkspace from "@/components/chat/AgentChatWorkspace";

export default function AgentChatPage({ params }: { params: { id: string } }) {
  return (
    <div className="h-full">
      <AgentChatWorkspace agentId={params.id} />
    </div>
  );
}
