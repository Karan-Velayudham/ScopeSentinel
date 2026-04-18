import AgentChatWorkspace from "@/components/chat/AgentChatWorkspace";

export default async function AgentChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="-m-6 md:-m-8 h-[calc(100vh-4rem)]">
      <AgentChatWorkspace agentId={id} />
    </div>
  );
}
