import { render, screen, fireEvent } from '@testing-library/react'
import { PlanReviewPanel } from './plan-review'
import '@testing-library/jest-dom'

jest.mock('react-markdown', () => {
    const MockReactMarkdown = (props: { children: React.ReactNode }) => <div data-testid="markdown">{props.children}</div>;
    MockReactMarkdown.displayName = 'ReactMarkdown';
    return MockReactMarkdown;
});
jest.mock('remark-gfm', () => () => { })

describe('PlanReviewPanel', () => {
    it('renders proposed changes markdown and review tools', () => {
        render(<PlanReviewPanel runId="run-126" />)

        // Should display the Action Required card
        expect(screen.getByText(/Action Required: Review Plan/i)).toBeInTheDocument()
        expect(screen.getByText(/Proposed Changes/i)).toBeInTheDocument()

        // Should display the action buttons
        expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Request Changes/i })).toBeInTheDocument()
    })

    it('switches to modifying state when Request Changes is clicked', () => {
        render(<PlanReviewPanel runId="run-126" />)

        const requestChangesBtn = screen.getByRole('button', { name: /Request Changes/i })
        fireEvent.click(requestChangesBtn)

        // Assert Textarea is visible
        expect(screen.getByPlaceholderText(/Provide feedback on what needs to change/i)).toBeInTheDocument()
    })
})
