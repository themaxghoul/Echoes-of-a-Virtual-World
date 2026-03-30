import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { 
  Shield, FileText, Globe, AlertTriangle, 
  CheckCircle, ArrowLeft, Scale, Lock
} from 'lucide-react';

const COMPANY_INFO = {
  name: "ApexForge Collective",
  address: "901 35th Ave, Tuscaloosa, AL 35401",
  phone: "(205) 233-4835",
  email: "legal@apexforge.io",
  website: "https://apexforge.io"
};

const TermsOfService = () => {
  const navigate = useNavigate();
  const [accepted, setAccepted] = useState({
    tos: false,
    privacy: false,
    earnings: false,
    age: false
  });
  
  const allAccepted = Object.values(accepted).every(v => v);
  
  const handleAcceptAll = () => {
    if (allAccepted) {
      localStorage.setItem('tos_accepted', new Date().toISOString());
      localStorage.setItem('tos_version', '1.0.0');
      navigate('/auth');
    }
  };
  
  return (
    <div className="min-h-screen bg-obsidian text-foreground p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button variant="ghost" onClick={() => navigate('/')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-cinzel text-3xl text-gold">Terms of Service</h1>
            <p className="text-muted-foreground">{COMPANY_INFO.name}</p>
          </div>
        </div>
        
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <Card 
            className={`p-4 cursor-pointer transition-all ${accepted.tos ? 'border-green-500' : 'border-border/50'}`}
            onClick={() => setAccepted(a => ({ ...a, tos: !a.tos }))}
          >
            <div className="flex items-center gap-3 mb-2">
              <FileText className={`w-5 h-5 ${accepted.tos ? 'text-green-500' : 'text-gold'}`} />
              <span className="font-cinzel">Terms of Service</span>
              {accepted.tos && <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />}
            </div>
            <p className="text-xs text-muted-foreground">General usage terms</p>
          </Card>
          
          <Card 
            className={`p-4 cursor-pointer transition-all ${accepted.privacy ? 'border-green-500' : 'border-border/50'}`}
            onClick={() => setAccepted(a => ({ ...a, privacy: !a.privacy }))}
          >
            <div className="flex items-center gap-3 mb-2">
              <Lock className={`w-5 h-5 ${accepted.privacy ? 'text-green-500' : 'text-gold'}`} />
              <span className="font-cinzel">Privacy Policy</span>
              {accepted.privacy && <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />}
            </div>
            <p className="text-xs text-muted-foreground">Data handling practices</p>
          </Card>
          
          <Card 
            className={`p-4 cursor-pointer transition-all ${accepted.earnings ? 'border-green-500' : 'border-border/50'}`}
            onClick={() => setAccepted(a => ({ ...a, earnings: !a.earnings }))}
          >
            <div className="flex items-center gap-3 mb-2">
              <Scale className={`w-5 h-5 ${accepted.earnings ? 'text-green-500' : 'text-gold'}`} />
              <span className="font-cinzel">Earnings Agreement</span>
              {accepted.earnings && <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />}
            </div>
            <p className="text-xs text-muted-foreground">Real-world income terms</p>
          </Card>
        </div>
        
        {/* Main Content */}
        <Card className="bg-surface/50 border-border/30 mb-6">
          <ScrollArea className="h-[50vh] p-6">
            <div className="prose prose-invert max-w-none">
              <h2 className="text-gold font-cinzel">TERMS OF SERVICE AGREEMENT</h2>
              <p className="text-sm text-muted-foreground">Last Updated: March 2026 | Version 1.0.0</p>
              
              <h3 className="text-gold">1. ACCEPTANCE OF TERMS</h3>
              <p>
                By accessing or using AI Village: The Echoes ("the Game") and its associated 
                earnings platform ("ApexForge Collective"), you agree to be bound by these 
                Terms of Service. If you do not agree to these terms, do not use the service.
              </p>
              
              <h3 className="text-gold">2. COMPANY INFORMATION</h3>
              <p>
                <strong>{COMPANY_INFO.name}</strong><br />
                {COMPANY_INFO.address}<br />
                Phone: {COMPANY_INFO.phone}<br />
                Email: {COMPANY_INFO.email}
              </p>
              
              <h3 className="text-gold">3. ELIGIBILITY</h3>
              <p>To participate in earnings activities, you must:</p>
              <ul>
                <li>Be at least 18 years of age</li>
                <li>Reside in a supported geographic region (see Geographic Restrictions)</li>
                <li>Provide accurate identity verification when requested</li>
                <li>Have legal capacity to enter into binding agreements</li>
                <li>Not be prohibited from participating by any applicable laws</li>
              </ul>
              
              <h3 className="text-gold">4. EARNINGS PROGRAM</h3>
              <h4>4.1 Income Streams</h4>
              <p>The platform offers various ways to earn real-world income:</p>
              <ul>
                <li><strong>Micro Tasks:</strong> Data labeling, content moderation, transcription</li>
                <li><strong>Surveys:</strong> Market research and opinion surveys</li>
                <li><strong>Compute Sharing:</strong> Optional sharing of device resources (requires explicit consent)</li>
                <li><strong>Affiliate Programs:</strong> Referral commissions</li>
                <li><strong>Blockchain Activities:</strong> Transaction verification and rewards</li>
              </ul>
              
              <h4>4.2 Payment Terms</h4>
              <ul>
                <li>Minimum withdrawal amount: $1.00 USD</li>
                <li><strong>Withdrawal fee: $0.25 per transaction</strong> (supports platform operations)</li>
                <li>Payments processed within 1-3 business days</li>
                <li>Supported methods: PayPal, Crypto Wallet, Bank Transfer</li>
                <li>All earnings are reported and may be subject to taxation</li>
              </ul>
              
              <h4>4.3 Earnings Disclaimer</h4>
              <p className="bg-yellow-500/10 p-3 rounded border border-yellow-500/30">
                <AlertTriangle className="inline w-4 h-4 mr-2 text-yellow-500" />
                <strong>IMPORTANT:</strong> Earnings vary based on task availability, completion quality, 
                time invested, and geographic location. We do not guarantee any specific income level. 
                Typical earnings range from $5-15 per hour depending on task type and user efficiency.
              </p>
              
              <h3 className="text-gold">5. COMPUTE SHARING (OPTIONAL)</h3>
              <p>
                If you opt into the Compute Sharing program, you agree to allow the platform 
                to utilize unused processing power from your device. This is entirely optional 
                and can be disabled at any time.
              </p>
              <ul>
                <li>Requires explicit opt-in consent</li>
                <li>You control resource allocation limits</li>
                <li>No personal data is accessed</li>
                <li>Earnings based on resources contributed</li>
                <li>May affect device battery and performance</li>
              </ul>
              
              <h3 className="text-gold">6. AI NPC CLOUD GAMING</h3>
              <p>
                The platform includes AI-powered NPCs that can play games autonomously. 
                These NPCs operate on cloud infrastructure and can be transferred between games.
              </p>
              <ul>
                <li>AI NPCs are for entertainment and demonstration purposes</li>
                <li>Cloud controllers require internet connectivity</li>
                <li>Game emulation is provided for legally owned content only</li>
                <li>Users must comply with game publishers' terms of service</li>
              </ul>
              
              <h3 className="text-gold">7. CRYPTOCURRENCY & BLOCKCHAIN</h3>
              <p>
                The platform may integrate with cryptocurrency networks. By participating in 
                blockchain activities, you acknowledge:
              </p>
              <ul>
                <li>Cryptocurrency values are volatile</li>
                <li>Transactions on blockchain are irreversible</li>
                <li>You are responsible for wallet security</li>
                <li>Network fees may apply to transactions</li>
                <li>Compliance with local cryptocurrency regulations is your responsibility</li>
              </ul>
              
              <h3 className="text-gold">8. PROHIBITED ACTIVITIES</h3>
              <p>Users may NOT:</p>
              <ul>
                <li>Use bots or automation to complete tasks</li>
                <li>Submit fraudulent or low-quality work</li>
                <li>Create multiple accounts to exploit the system</li>
                <li>Attempt to manipulate earnings or game systems</li>
                <li>Share account credentials with others</li>
                <li>Engage in money laundering or illegal activities</li>
                <li>Violate any applicable laws or regulations</li>
              </ul>
              
              <h3 className="text-gold">9. ACCOUNT TERMINATION</h3>
              <p>
                We reserve the right to suspend or terminate accounts that violate these terms. 
                Upon termination:
              </p>
              <ul>
                <li>Pending earnings may be forfeited if termination is due to violations</li>
                <li>You may appeal within 30 days</li>
                <li>Legitimate earnings will be paid out within 30 days of account closure</li>
              </ul>
              
              <h3 className="text-gold">10. LIMITATION OF LIABILITY</h3>
              <p>
                TO THE MAXIMUM EXTENT PERMITTED BY LAW, {COMPANY_INFO.name.toUpperCase()} SHALL NOT 
                BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, 
                INCLUDING LOSS OF PROFITS, DATA, OR GOODWILL.
              </p>
              
              <h3 className="text-gold">11. DISPUTE RESOLUTION</h3>
              <p>
                Any disputes shall be resolved through binding arbitration in Tuscaloosa County, 
                Alabama, in accordance with the rules of the American Arbitration Association.
              </p>
              
              <h3 className="text-gold">12. MODIFICATIONS</h3>
              <p>
                We may modify these terms at any time. Continued use after modifications 
                constitutes acceptance of the updated terms.
              </p>
              
              <h3 className="text-gold">13. CONTACT</h3>
              <p>
                For questions about these terms, contact us at:<br />
                <strong>Email:</strong> {COMPANY_INFO.email}<br />
                <strong>Phone:</strong> {COMPANY_INFO.phone}<br />
                <strong>Address:</strong> {COMPANY_INFO.address}
              </p>
              
              <hr className="border-border/30 my-8" />
              
              <h2 className="text-gold font-cinzel">PRIVACY POLICY</h2>
              
              <h3 className="text-gold">Data We Collect</h3>
              <ul>
                <li>Account information (email, username, password hash)</li>
                <li>Identity verification documents (for earnings over $100)</li>
                <li>Task completion data and performance metrics</li>
                <li>Device information (for compute sharing, if opted in)</li>
                <li>Payment information (processed securely via third-party providers)</li>
                <li>Geographic location (country-level, for eligibility)</li>
              </ul>
              
              <h3 className="text-gold">How We Use Data</h3>
              <ul>
                <li>Process earnings and payments</li>
                <li>Improve task quality and matching</li>
                <li>Prevent fraud and abuse</li>
                <li>Comply with legal requirements</li>
                <li>Communicate important updates</li>
              </ul>
              
              <h3 className="text-gold">Data Sharing</h3>
              <p>We do NOT sell your personal data. We may share data with:</p>
              <ul>
                <li>Payment processors (to process withdrawals)</li>
                <li>Task providers (anonymized work data only)</li>
                <li>Law enforcement (when legally required)</li>
              </ul>
              
              <h3 className="text-gold">Your Rights</h3>
              <ul>
                <li>Access your personal data</li>
                <li>Request data deletion</li>
                <li>Opt out of optional features</li>
                <li>Export your data</li>
              </ul>
            </div>
          </ScrollArea>
        </Card>
        
        {/* Age Verification */}
        <Card className="p-4 mb-6 bg-surface/50 border-border/30">
          <div className="flex items-center gap-3">
            <Checkbox 
              id="age"
              checked={accepted.age}
              onCheckedChange={(checked) => setAccepted(a => ({ ...a, age: checked }))}
            />
            <label htmlFor="age" className="text-sm cursor-pointer">
              I confirm that I am at least <strong>18 years of age</strong> and have the legal 
              capacity to enter into this agreement.
            </label>
          </div>
        </Card>
        
        {/* Accept Button */}
        <div className="flex justify-between items-center">
          <Button variant="ghost" onClick={() => navigate('/')}>
            Decline
          </Button>
          
          <Button 
            onClick={handleAcceptAll}
            disabled={!allAccepted}
            className={allAccepted ? 'bg-gold text-black hover:bg-gold-light' : ''}
          >
            {allAccepted ? 'Accept & Continue' : 'Accept All Terms to Continue'}
          </Button>
        </div>
        
        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-border/30 text-center text-xs text-muted-foreground">
          <p>{COMPANY_INFO.name} | {COMPANY_INFO.address}</p>
          <p>Phone: {COMPANY_INFO.phone} | Email: {COMPANY_INFO.email}</p>
          <p className="mt-2">© 2026 ApexForge Collective. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
};

export default TermsOfService;
