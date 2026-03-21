import { render, screen, fireEvent } from '@testing-library/react'
import IntegrationsPage from './page'
import '@testing-library/jest-dom'

describe('IntegrationsPage', () => {
    it('renders integrations correctly', () => {
        render(<IntegrationsPage />)

        expect(screen.getByText('GitHub')).toBeInTheDocument()
        expect(screen.getByText('Jira')).toBeInTheDocument()
        expect(screen.getByText('Slack')).toBeInTheDocument()
        expect(screen.getByText('OpenAI API')).toBeInTheDocument()
    })

    it('opens API key dialog for OpenAI', () => {
        render(<IntegrationsPage />)

        const buttons = screen.getAllByRole('button', { name: /Provide API Key/i })
        fireEvent.click(buttons[0])

        expect(screen.getByText('Connect OpenAI API')).toBeInTheDocument()
        expect(screen.getByLabelText('API Key')).toBeInTheDocument()
    })
})
