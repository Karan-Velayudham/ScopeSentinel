import { render, screen } from '@testing-library/react'
import { RunTimeline } from './run-timeline'
import '@testing-library/jest-dom'

describe('RunTimeline', () => {
    it('renders a list of mock steps based on the run details timeline requirements', () => {
        render(<RunTimeline runId="run-123" />)

        // verify some of the steps format and content
        expect(screen.getByText('Fetch Ticket Details')).toBeInTheDocument()
        expect(screen.getByText('Analyze Codebase')).toBeInTheDocument()
        expect(screen.getByText('Generate Implementation Plan')).toBeInTheDocument()
    })
})
