import React, { useState } from 'react';
import {
  Users,
  Search,
  Box,
  ShieldCheck,
  Wrench,
  Code,
  BarChart2,
  CheckCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';
import { SubagentActivity } from '../../types';

interface SubagentTeamBarProps {
  activities?: SubagentActivity[];
}

interface AgentMeta {
  key: string;
  name: string;
  role: string;
  pipelineStage: string;
  standbyDescription: string;
  icon: React.ComponentType<{ className?: string }>;
}

const AGENT_ROSTER: AgentMeta[] = [
  {
    key: 'Interviewer',
    name: 'Interviewer',
    role: 'Discovery Analyst',
    pipelineStage: 'Discovery',
    standbyDescription: 'Interviews & clarifies business logic one by one',
    icon: Search,
  },
  {
    key: 'Architect',
    name: 'Architect',
    role: 'Data Model & Workflows',
    pipelineStage: 'Drafting',
    standbyDescription: 'Queued: synthesizes DocTypes & workflows on confirmation',
    icon: Box,
  },
  {
    key: 'Validator',
    name: 'Validator',
    role: 'Frappe Rule Engine',
    pipelineStage: 'Validation',
    standbyDescription: 'Queued: audits schema against 20+ Frappe v15 constraints',
    icon: ShieldCheck,
  },
  {
    key: 'Healer',
    name: 'Healer',
    role: 'Self-Healing Specialist',
    pipelineStage: 'Healing',
    standbyDescription: 'Queued: applies deterministic repair patches',
    icon: Wrench,
  },
  {
    key: 'ScriptWriter',
    name: 'ScriptWriter',
    role: 'Controller & Client Scripts',
    pipelineStage: 'Scripting',
    standbyDescription: 'Queued: generates Python controllers & Client Scripts',
    icon: Code,
  },
  {
    key: 'ReportBuilder',
    name: 'ReportBuilder',
    role: 'Analytics & Dashboards',
    pipelineStage: 'Reporting',
    standbyDescription: 'Queued: creates script reports & Workspace dashboards',
    icon: BarChart2,
  },
  {
    key: 'QAAgent',
    name: 'QA Agent',
    role: 'Bench Runner & QA',
    pipelineStage: 'Testing',
    standbyDescription: 'Queued: runs Frappe unit tests on local bench',
    icon: CheckCircle,
  },
  {
    key: 'Documenter',
    name: 'Documenter',
    role: 'Docs & ERD Synthesizer',
    pipelineStage: 'Documentation',
    standbyDescription: 'Queued: compiles README, ERD diagrams & user guides',
    icon: FileText,
  },
];

export const SubagentTeamBar: React.FC<SubagentTeamBarProps> = ({ activities = [] }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Safe mapping of activities by agent key and role
  const activityMap = React.useMemo(() => {
    const map = new Map<string, SubagentActivity>();
    if (!Array.isArray(activities)) return map;
    for (const act of activities) {
      if (!act) continue;
      if (act.agent) map.set(String(act.agent).toLowerCase(), act);
      if (act.role) map.set(String(act.role).toLowerCase(), act);
    }
    return map;
  }, [activities]);

  const safeActivities = Array.isArray(activities) ? activities : [];
  const activeAgent = safeActivities.find((a) => a && a.status === 'active');
  const activeCount = safeActivities.filter((a) => a && a.status === 'active').length;
  const completedCount = safeActivities.filter((a) => a && a.status === 'completed').length;

  return (
    <div className="w-full bg-[var(--surface)] border-b border-[var(--border)] px-4 py-2 flex flex-col gap-2 transition-all select-none">
      {/* Top compact bar */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1.5 font-medium text-[var(--text)]">
            <Users className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span>Autonomous Subagents</span>
          </div>

          <span className="text-[var(--border)]">|</span>

          {activeAgent ? (
            <div className="flex items-center gap-1.5 text-xs text-[var(--accent)] truncate">
              <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
              <span className="font-medium truncate">
                {activeAgent.agent}: {activeAgent.action}
              </span>
            </div>
          ) : completedCount > 0 ? (
            <div className="flex items-center gap-1.5 text-xs text-[var(--muted)] truncate">
              <CheckCircle className="w-3.5 h-3.5 text-[var(--ok)] flex-shrink-0" />
              <span className="truncate">{completedCount} tasks completed</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-[var(--muted)] truncate">
              <span>Ready to assist</span>
              <span className="hidden sm:inline text-[var(--border)]">•</span>
              <span className="hidden sm:inline">Interviewer in Discovery (7 specialists queued)</span>
            </div>
          )}
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)] transition-colors"
          aria-expanded={isExpanded}
          aria-label="Toggle subagent team details"
        >
          <span>{isExpanded ? 'Hide' : 'Team'}</span>
          <span className="px-1 py-0.2 rounded-pill bg-[var(--border)] text-[10px]">
            {activeCount > 0 ? `${activeCount} active` : '8 agents'}
          </span>
          {isExpanded ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* Expanded Team Grid */}
      {isExpanded && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-[var(--border)]">
          {AGENT_ROSTER.map((agent) => {
            const Icon = agent.icon;
            const activity =
              (agent.key ? activityMap.get(agent.key.toLowerCase()) : undefined) ||
              (agent.name ? activityMap.get(agent.name.toLowerCase()) : undefined);
            const status = activity?.status || 'idle';

            let statusBadge = 'bg-[var(--border)] text-[var(--muted)]';
            let dotColor = 'bg-[var(--muted)]';
            let cardBorder = 'border-[var(--border)]';
            let displayStatus = status === 'idle' ? 'standby' : status;

            if (status === 'active') {
              statusBadge = 'bg-[var(--accent)]/15 text-[var(--accent)] font-medium';
              dotColor = 'bg-[var(--accent)] animate-ping';
              cardBorder = 'border-[var(--accent)]';
            } else if (status === 'completed') {
              statusBadge = 'bg-[var(--ok)]/15 text-[var(--ok)]';
              dotColor = 'bg-[var(--ok)]';
            } else if (status === 'failed') {
              statusBadge = 'bg-[var(--err)]/15 text-[var(--err)]';
              dotColor = 'bg-[var(--err)]';
            }

            return (
              <div
                key={agent.key}
                className={`p-2 rounded-card border ${cardBorder} bg-[var(--bg)] flex flex-col gap-1 text-left transition-all`}
              >
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5 truncate">
                    <Icon className="w-3.5 h-3.5 text-[var(--text)]" />
                    <span className="font-medium text-xs text-[var(--text)] truncate">
                      {agent.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
                    <span className={`px-1 py-0.2 rounded text-[9px] capitalize ${statusBadge}`}>
                      {displayStatus}
                    </span>
                  </div>
                </div>

                <div className="text-[10px] text-[var(--muted)] truncate" title={activity?.action || agent.standbyDescription}>
                  {activity?.action || agent.standbyDescription || agent.role}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
