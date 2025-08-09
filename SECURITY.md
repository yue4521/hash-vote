# Security Policy

## Supported Versions

We actively maintain and provide security updates for the following versions of HashVote:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | Yes                |
| < 1.0   | No                 |

## Reporting a Vulnerability

The HashVote team and community take security bugs seriously. We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.

### How to Report a Security Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email**: Send a detailed report to the project maintainer
2. **GitHub Security Advisories**: Use GitHub's private vulnerability reporting feature
3. **Direct Message**: Contact the maintainer through GitHub

### What to Include

Please include the following information in your security report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

### Response Timeline

- **Initial Response**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Investigation**: We will investigate and validate the vulnerability within 7 days
- **Resolution**: For confirmed vulnerabilities, we will develop and test a fix within 30 days
- **Disclosure**: We will coordinate with you on the timing of public disclosure

## Security Considerations for HashVote

### Proof-of-Work Implementation

HashVote implements a Proof-of-Work based voting system with the following security characteristics:

#### Strengths

- **Computational Commitment**: 18-bit leading zero requirement provides meaningful computational cost
- **Chain Integrity**: Cryptographic linking prevents tampering with historical votes
- **Duplicate Prevention**: (poll_id, voter_hash) uniqueness constraint prevents double voting
- **Transparent Audit**: Complete voting history is cryptographically verifiable

#### Known Limitations

- **Sybil Attack Vulnerability**: voter_hash management relies on external identity verification
- **Centralized Architecture**: Single-node deployment lacks distributed consensus mechanisms
- **Resource-based Exclusion**: PoW requirements may limit participation based on computational resources
- **Time-based Attacks**: Server-controlled timestamps could be manipulated

### Security Best Practices

When deploying HashVote in production:

1. **Identity Management**: Implement robust voter_hash generation and verification
2. **Rate Limiting**: Deploy appropriate rate limiting to prevent DoS attacks
3. **TLS/HTTPS**: Always use encrypted connections for API communications
4. **Input Validation**: Validate all inputs to prevent injection attacks
5. **Database Security**: Secure the SQLite database file with appropriate permissions
6. **Monitoring**: Implement logging and monitoring for suspicious activities

### Threat Model

HashVote is designed to protect against:

- Vote tampering after submission
- Unauthorized vote modification
- Double voting with same voter credentials
- Historical vote alteration

HashVote does NOT protect against:

- Sybil attacks (requires external identity verification)
- Coercion or vote buying (inherent to digital voting)
- Denial of service attacks
- Compromise of the server infrastructure

## Vulnerability Disclosure Policy

### Safe Harbor

When conducting vulnerability research according to this policy:

- We will not pursue or support any legal action related to your research
- We will work with you to understand and resolve the issue quickly
- We will recognize your contribution if you are the first to report the issue and we make a code or configuration change based on the issue

### Guidelines for Researchers

- Please provide reasonable time for us to address the vulnerability before public disclosure
- Make a good faith effort to avoid privacy violations, destruction of data, and interruption or degradation of services
- Only interact with accounts you own or with explicit permission of the account holder

## Contact

For security-related questions or to report vulnerabilities, please contact the project maintainer through GitHub.

## Acknowledgments

We would like to thank the security researchers and community members who help keep HashVote secure.