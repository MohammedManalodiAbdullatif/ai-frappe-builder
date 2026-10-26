import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { SubagentTeamBar } from '../components/chat/SubagentTeamBar';
import { SubagentActivity } from '../types';

describe('SubagentTeamBar Component', () => {
  it('renders idle state when no activities present', () => {
    render(<SubagentTeamBar activities={[]} />);
    expect(screen.getByText('Autonomous Subagents')).toBeDefined();
    expect(screen.getByText('Ready to assist')).toBeDefined();
    expect(screen.getByText('8 agents')).toBeDefined();
  });

  it('displays active agent and ongoing action', () => {
    const activities: SubagentActivity[] = [
      {
        agent: 'Architect',
        role: 'Data Model & Workflows',
        status: 'active',
        action: 'Designing DocTypes, fields, and workflows...',
      },
    ];

    render(<SubagentTeamBar activities={activities} />);
    expect(screen.getByText(/Architect: Designing DocTypes/)).toBeDefined();
    expect(screen.getByText('1 active')).toBeDefined();
  });

  it('toggles team roster card grid on expand button click', () => {
    const activities: SubagentActivity[] = [
      {
        agent: 'Validator',
        role: 'Frappe Rule Engine',
        status: 'completed',
        action: 'Audited 20+ Frappe v15 constraints',
      },
    ];

    render(<SubagentTeamBar activities={activities} />);
    const toggleBtn = screen.getByLabelText('Toggle subagent team details');
    expect(screen.queryByText('ScriptWriter')).toBeNull();

    fireEvent.click(toggleBtn);
    expect(screen.getByText('ScriptWriter')).toBeDefined();
    expect(screen.getByText('Healer')).toBeDefined();
    expect(screen.getByText('QA Agent')).toBeDefined();
    expect(screen.getByText('Documenter')).toBeDefined();
  });
});
