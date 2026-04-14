import AgentChatWorkspace from "@/components/chat/AgentChatWorkspace";

export default async function AgentChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="h-full">
      <AgentChatWorkspace agentId={id} />
    </div>
  );
}
