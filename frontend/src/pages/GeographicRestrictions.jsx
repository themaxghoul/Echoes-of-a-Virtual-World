import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { 
  Globe, Check, X, Search, MapPin, 
  AlertTriangle, ArrowLeft, Shield
} from 'lucide-react';

const SUPPORTED_REGIONS = {
  "US": { name: "United States", full_support: true },
  "CA": { name: "Canada", full_support: true },
  "GB": { name: "United Kingdom", full_support: true },
  "DE": { name: "Germany", full_support: true },
  "FR": { name: "France", full_support: true },
  "AU": { name: "Australia", full_support: true },
  "JP": { name: "Japan", full_support: true },
  "KR": { name: "South Korea", full_support: true },
  "SG": { name: "Singapore", full_support: true },
  "NL": { name: "Netherlands", full_support: true },
  "SE": { name: "Sweden", full_support: true },
  "NO": { name: "Norway", full_support: true },
  "DK": { name: "Denmark", full_support: true },
  "FI": { name: "Finland", full_support: true },
  "IE": { name: "Ireland", full_support: true },
  "NZ": { name: "New Zealand", full_support: true },
  "CH": { name: "Switzerland", full_support: true },
  "AT": { name: "Austria", full_support: true },
  "BE": { name: "Belgium", full_support: true },
  "IT": { name: "Italy", full_support: true },
  "ES": { name: "Spain", full_support: true },
  "PT": { name: "Portugal", full_support: true },
  "PL": { name: "Poland", full_support: true },
  "CZ": { name: "Czech Republic", full_support: true },
  "HU": { name: "Hungary", full_support: true },
  "RO": { name: "Romania", full_support: true },
  "BG": { name: "Bulgaria", full_support: true },
  "HR": { name: "Croatia", full_support: true },
  "SK": { name: "Slovakia", full_support: true },
  "SI": { name: "Slovenia", full_support: true },
  "LT": { name: "Lithuania", full_support: true },
  "LV": { name: "Latvia", full_support: true },
  "EE": { name: "Estonia", full_support: true },
  "MT": { name: "Malta", full_support: true },
  "CY": { name: "Cyprus", full_support: true },
  "LU": { name: "Luxembourg", full_support: true },
  "MX": { name: "Mexico", full_support: true },
  "BR": { name: "Brazil", full_support: true },
  "AR": { name: "Argentina", full_support: true },
  "CL": { name: "Chile", full_support: true },
  "CO": { name: "Colombia", full_support: true },
  "PE": { name: "Peru", full_support: true },
  "IN": { name: "India", full_support: true },
  "PH": { name: "Philippines", full_support: true },
  "TH": { name: "Thailand", full_support: true },
  "MY": { name: "Malaysia", full_support: true },
  "ID": { name: "Indonesia", full_support: true },
  "VN": { name: "Vietnam", full_support: true },
  "ZA": { name: "South Africa", full_support: true },
  "NG": { name: "Nigeria", full_support: true },
  "KE": { name: "Kenya", full_support: true },
  "GH": { name: "Ghana", full_support: true },
  "EG": { name: "Egypt", full_support: true },
  "MA": { name: "Morocco", full_support: true },
  "TN": { name: "Tunisia", full_support: true },
};

const RESTRICTED_REGIONS = {
  "CU": { name: "Cuba", reason: "US Sanctions" },
  "IR": { name: "Iran", reason: "US Sanctions" },
  "KP": { name: "North Korea", reason: "International Sanctions" },
  "SY": { name: "Syria", reason: "US Sanctions" },
  "RU": { name: "Russia", reason: "International Sanctions" },
  "BY": { name: "Belarus", reason: "International Sanctions" },
};

const GeographicRestrictions = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [detectedCountry, setDetectedCountry] = useState(null);
  const [isEligible, setIsEligible] = useState(null);
  
  useEffect(() => {
    // Try to detect user's country
    detectCountry();
  }, []);
  
  const detectCountry = async () => {
    try {
      // Use a free geo-IP service
      const response = await fetch('https://ipapi.co/json/');
      const data = await response.json();
      if (data.country_code) {
        setDetectedCountry({
          code: data.country_code,
          name: data.country_name
        });
        
        if (SUPPORTED_REGIONS[data.country_code]) {
          setIsEligible(true);
        } else if (RESTRICTED_REGIONS[data.country_code]) {
          setIsEligible(false);
        } else {
          setIsEligible(null); // Unknown
        }
      }
    } catch (error) {
      console.log('Could not detect country');
    }
  };
  
  const filteredSupported = Object.entries(SUPPORTED_REGIONS).filter(([code, data]) => 
    data.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    code.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  const filteredRestricted = Object.entries(RESTRICTED_REGIONS).filter(([code, data]) => 
    data.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    code.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  return (
    <div className="min-h-screen bg-obsidian text-foreground p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button variant="ghost" onClick={() => navigate('/terms')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-cinzel text-3xl text-gold">Geographic Eligibility</h1>
            <p className="text-muted-foreground">ApexForge Collective Earnings Program</p>
          </div>
        </div>
        
        {/* Detection Result */}
        {detectedCountry && (
          <Card className={`p-6 mb-6 ${
            isEligible === true ? 'border-green-500 bg-green-500/10' :
            isEligible === false ? 'border-red-500 bg-red-500/10' :
            'border-yellow-500 bg-yellow-500/10'
          }`}>
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                isEligible === true ? 'bg-green-500' :
                isEligible === false ? 'bg-red-500' :
                'bg-yellow-500'
              }`}>
                {isEligible === true ? <Check className="w-6 h-6 text-white" /> :
                 isEligible === false ? <X className="w-6 h-6 text-white" /> :
                 <AlertTriangle className="w-6 h-6 text-black" />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-muted-foreground" />
                  <span className="text-lg font-medium">Detected Location: {detectedCountry.name}</span>
                  <Badge className="ml-2">{detectedCountry.code}</Badge>
                </div>
                <p className={`text-sm ${
                  isEligible === true ? 'text-green-400' :
                  isEligible === false ? 'text-red-400' :
                  'text-yellow-400'
                }`}>
                  {isEligible === true ? '✓ You are eligible for the ApexForge Earnings Program!' :
                   isEligible === false ? '✗ Unfortunately, earnings features are not available in your region.' :
                   '? Your region is not in our standard list. Contact support for eligibility.'}
                </p>
              </div>
            </div>
            
            {isEligible === false && RESTRICTED_REGIONS[detectedCountry.code] && (
              <div className="mt-4 p-3 bg-red-500/10 rounded border border-red-500/30">
                <p className="text-sm text-red-300">
                  <strong>Reason:</strong> {RESTRICTED_REGIONS[detectedCountry.code].reason}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  This restriction is due to international sanctions and legal requirements. 
                  We cannot offer financial services in your region at this time.
                </p>
              </div>
            )}
          </Card>
        )}
        
        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search countries..."
            className="pl-10 bg-surface border-border/50"
          />
        </div>
        
        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Card className="p-4 bg-green-500/10 border-green-500/30">
            <div className="flex items-center gap-3">
              <Check className="w-6 h-6 text-green-500" />
              <div>
                <div className="text-2xl font-bold text-green-400">{Object.keys(SUPPORTED_REGIONS).length}</div>
                <div className="text-sm text-muted-foreground">Supported Countries</div>
              </div>
            </div>
          </Card>
          <Card className="p-4 bg-red-500/10 border-red-500/30">
            <div className="flex items-center gap-3">
              <X className="w-6 h-6 text-red-500" />
              <div>
                <div className="text-2xl font-bold text-red-400">{Object.keys(RESTRICTED_REGIONS).length}</div>
                <div className="text-sm text-muted-foreground">Restricted Regions</div>
              </div>
            </div>
          </Card>
        </div>
        
        {/* Supported Regions */}
        <Card className="mb-6 bg-surface/50 border-border/30">
          <div className="p-4 border-b border-border/30 flex items-center gap-2">
            <Globe className="w-5 h-5 text-green-500" />
            <h2 className="font-cinzel text-lg text-gold">Supported Regions</h2>
            <Badge className="ml-auto bg-green-500/20 text-green-400">Full Earnings Access</Badge>
          </div>
          <ScrollArea className="h-64">
            <div className="p-4 grid grid-cols-2 md:grid-cols-3 gap-2">
              {filteredSupported.map(([code, data]) => (
                <div 
                  key={code}
                  className="flex items-center gap-2 p-2 bg-green-500/5 rounded hover:bg-green-500/10 transition-colors"
                >
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                  <span className="text-sm truncate">{data.name}</span>
                  <Badge variant="outline" className="ml-auto text-xs">{code}</Badge>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>
        
        {/* Restricted Regions */}
        <Card className="mb-6 bg-surface/50 border-border/30">
          <div className="p-4 border-b border-border/30 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h2 className="font-cinzel text-lg text-gold">Restricted Regions</h2>
            <Badge className="ml-auto bg-red-500/20 text-red-400">Earnings Unavailable</Badge>
          </div>
          <div className="p-4">
            {filteredRestricted.map(([code, data]) => (
              <div 
                key={code}
                className="flex items-center gap-3 p-3 bg-red-500/5 rounded mb-2"
              >
                <X className="w-5 h-5 text-red-500 flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{data.name}</span>
                    <Badge variant="outline" className="text-xs">{code}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{data.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
        
        {/* Legal Notice */}
        <Card className="p-4 bg-yellow-500/5 border-yellow-500/30">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-yellow-400 mb-2">Important Legal Notice</h3>
              <p className="text-sm text-muted-foreground">
                Geographic restrictions are in place to comply with international sanctions, 
                anti-money laundering regulations, and local laws. These restrictions may change 
                as regulations evolve. Using VPNs or other methods to circumvent geographic 
                restrictions is prohibited and may result in account termination and forfeiture 
                of earnings.
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                If you believe you are incorrectly restricted or have questions about eligibility 
                in your region, please contact us at: <strong>legal@apexforge.io</strong>
              </p>
            </div>
          </div>
        </Card>
        
        {/* Contact */}
        <div className="mt-8 pt-4 border-t border-border/30 text-center text-xs text-muted-foreground">
          <p>ApexForge Collective | 901 35th Ave, Tuscaloosa, AL 35401</p>
          <p>Phone: (205) 233-4835 | Email: legal@apexforge.io</p>
        </div>
      </div>
    </div>
  );
};

export default GeographicRestrictions;
