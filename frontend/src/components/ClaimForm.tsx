// client/src/components/ClaimForm.tsx
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

interface FormData {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  branch: string;
  status: string;
  serviceStart: string;
  serviceEnd: string;
  dischargeType: string;
  claimTypes: string[];
  claimDescription: string;
  previousClaim: string;
}

// The "default" keyword has been removed from the line below to make it a named export.
export function ClaimForm() {
  const [formStep, setFormStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    branch: "",
    status: "",
    serviceStart: "",
    serviceEnd: "",
    dischargeType: "",
    claimTypes: [],
    claimDescription: "",
    previousClaim: "",
  });
  const { toast } = useToast();

  const updateFormData = (field: keyof FormData, value: string | string[]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCheckboxChange = (value: string) => {
    setFormData((prev) => {
      const currentTypes = [...prev.claimTypes];
      const index = currentTypes.indexOf(value);

      if (index === -1) {
        currentTypes.push(value);
      } else {
        currentTypes.splice(index, 1);
      }

      return { ...prev, claimTypes: currentTypes };
    });
  };

  const validateStep1 = () => {
    if (!formData.firstName.trim()) return "First name is required";
    if (!formData.lastName.trim()) return "Last name is required";
    if (!formData.email.trim()) return "Email is required";
    if (!formData.phone.trim()) return "Phone number is required";
    return null;
  };

  const validateStep2 = () => {
    if (!formData.branch) return "Branch of service is required";
    if (!formData.status) return "Current status is required";
    if (!formData.serviceStart) return "Service start date is required";
    if (!formData.dischargeType) return "Discharge type is required";
    return null;
  };

  const validateStep3 = () => {
    if (formData.claimTypes.length === 0)
      return "Please select at least one claim type";
    if (!formData.claimDescription.trim())
      return "Please provide a description of your claim";
    if (!formData.previousClaim)
      return "Please indicate if you've previously filed a claim";
    return null;
  };

  const nextStep = () => {
    let error = null;

    if (formStep === 1) {
      error = validateStep1();
    } else if (formStep === 2) {
      error = validateStep2();
    }

    if (error) {
      toast({
        title: "Validation Error",
        description: error,
        variant: "destructive",
      });
      return;
    }

    setFormStep((prev) => prev + 1);
  };

  const prevStep = () => {
    setFormStep((prev) => prev - 1);
  };

  const submitForm = async () => {
    const error = validateStep3();

    if (error) {
      toast({
        title: "Validation Error",
        description: error,
        variant: "destructive",
      });
      return;
    }

    try {
      await apiRequest("POST", "/api/claims", formData);

      toast({
        title: "Claim Submitted",
        description:
          "Your claim information has been submitted successfully. We'll be in touch soon!",
      });

      // Reset form
      setFormStep(1);
      setFormData({
        firstName: "",
        lastName: "",
        email: "",
        phone: "",
        branch: "",
        status: "",
        serviceStart: "",
        serviceEnd: "",
        dischargeType: "",
        claimTypes: [],
        claimDescription: "",
        previousClaim: "",
      });
    } catch (error) {
      toast({
        title: "Submission Error",
        description:
          "There was an error submitting your claim. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <section id="get-started" className="py-16 bg-neutral-100 chevron-bg">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-navy mb-4">
            Start Your Claim Process
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Take the first step toward getting the benefits you've earned. Our
            AI-powered system will guide you through the entire process.
          </p>
        </div>

        <Card className="max-w-4xl mx-auto bg-white rounded-lg shadow-sharp overflow-hidden">
          <div className="navy p-6">
            <h3 className="text-xl font-semibold text-white">
              Claim Assessment Form
            </h3>
            <p className="text-gray-300">
              Tell us about your service to get started
            </p>
          </div>

          <CardContent className="p-6">
            {/* Step 1: Personal Information */}
            {formStep === 1 && (
              <div className="space-y-6">
                <h4 className="font-semibold text-navy text-lg pb-2 border-b border-gray-200">
                  1. Personal Information
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label
                      htmlFor="firstName"
                      className="block text-muted-foreground mb-1"
                    >
                      First Name
                    </Label>
                    <Input
                      type="text"
                      id="firstName"
                      value={formData.firstName}
                      onChange={(e) => updateFormData("firstName", e.target.value)}
                      placeholder="Enter your first name"
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="lastName"
                      className="block text-muted-foreground mb-1"
                    >
                      Last Name
                    </Label>
                    <Input
                      type="text"
                      id="lastName"
                      value={formData.lastName}
                      onChange={(e) => updateFormData("lastName", e.target.value)}
                      placeholder="Enter your last name"
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="email"
                      className="block text-muted-foreground mb-1"
                    >
                      Email Address
                    </Label>
                    <Input
                      type="email"
                      id="email"
                      value={formData.email}
                      onChange={(e) => updateFormData("email", e.target.value)}
                      placeholder="Enter your email"
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="phone"
                      className="block text-muted-foreground mb-1"
                    >
                      Phone Number
                    </Label>
                    <Input
                      type="tel"
                      id="phone"
                      value={formData.phone}
                      onChange={(e) => updateFormData("phone", e.target.value)}
                      placeholder="(555) 555-5555"
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                    />
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <Button
                    type="button"
                    className="px-6 py-3 navy text-white rounded-md hover:bg-navy-light transition-colors"
                    onClick={nextStep}
                  >
                    Continue <i className="fas fa-arrow-right ml-2"></i>
                  </Button>
                </div>
              </div>
            )}

            {/* Step 2: Military Service */}
            {formStep === 2 && (
              <div className="space-y-6">
                <h4 className="font-semibold text-navy text-lg pb-2 border-b border-gray-200">
                  2. Military Service Details
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label
                      htmlFor="branch"
                      className="block text-muted-foreground mb-1"
                    >
                      Branch of Service
                    </Label>
                    <Select
                      value={formData.branch}
                      onValueChange={(value) => updateFormData("branch", value)}
                    >
                      <SelectTrigger className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy">
                        <SelectValue placeholder="Select branch" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="army">Army</SelectItem>
                          <SelectItem value="navy">Navy</SelectItem>
                          <SelectItem value="airforce">Air Force</SelectItem>
                          <SelectItem value="marines">Marine Corps</SelectItem>
                          <SelectItem value="coastguard">
                            Coast Guard
                          </SelectItem>
                          <SelectItem value="spacef">Space Force</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label
                      htmlFor="status"
                      className="block text-muted-foreground mb-1"
                    >
                      Current Status
                    </Label>
                    <Select
                      value={formData.status}
                      onValueChange={(value) => updateFormData("status", value)}
                    >
                      <SelectTrigger className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="active">Active Duty</SelectItem>
                          <SelectItem value="reserve">Reserve</SelectItem>
                          <SelectItem value="guard">National Guard</SelectItem>
                          <SelectItem value="veteran">Veteran</SelectItem>
                          <SelectItem value="retired">Retired</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label
                      htmlFor="serviceStart"
                      className="block text-muted-foreground mb-1"
                    >
                      Service Start Date
                    </Label>
                    <Input
                      type="date"
                      id="serviceStart"
                      value={formData.serviceStart}
                      onChange={(e) =>
                        updateFormData("serviceStart", e.target.value)
                      }
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="serviceEnd"
                      className="block text-muted-foreground mb-1"
                    >
                      Service End Date
                    </Label>
                    <Input
                      type="date"
                      id="serviceEnd"
                      value={formData.serviceEnd}
                      onChange={(e) =>
                        updateFormData("serviceEnd", e.target.value)
                      }
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <Label
                      htmlFor="dischargeType"
                      className="block text-muted-foreground mb-1"
                    >
                      Discharge Type
                    </Label>
                    <Select
                      value={formData.dischargeType}
                      onValueChange={(value) =>
                        updateFormData("dischargeType", value)
                      }
                    >
                      <SelectTrigger className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy">
                        <SelectValue placeholder="Select discharge type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="honorable">Honorable</SelectItem>
                          <SelectItem value="general">
                            General (Under Honorable Conditions)
                          </SelectItem>
                          <SelectItem value="other">
                            Other Than Honorable
                          </SelectItem>
                          <SelectItem value="bad">Bad Conduct</SelectItem>
                          <SelectItem value="dishonorable">
                            Dishonorable
                          </SelectItem>
                          <SelectItem value="entry">
                            Entry Level Separation
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="pt-4 flex justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    className="px-6 py-3 border border-navy text-navy rounded-md hover:bg-neutral-200 transition-colors"
                    onClick={prevStep}
                  >
                    <i className="fas fa-arrow-left mr-2"></i> Back
                  </Button>

                  <Button
                    type="button"
                    className="px-6 py-3 navy text-white rounded-md hover:bg-navy-light transition-colors"
                    onClick={nextStep}
                  >
                    Continue <i className="fas fa-arrow-right ml-2"></i>
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Claim Information */}
            {formStep === 3 && (
              <div className="space-y-6">
                <h4 className="font-semibold text-navy text-lg pb-2 border-b border-gray-200">
                  3. Claim Information
                </h4>

                <div className="space-y-6">
                  <div>
                    <Label className="block text-muted-foreground mb-3">
                      What type of claim are you interested in?
                    </Label>
                    <div className="space-y-3">
                      <div className="flex items-start">
                        <Checkbox
                          id="claimType1"
                          checked={formData.claimTypes.includes("disability")}
                          onCheckedChange={() =>
                            handleCheckboxChange("disability")
                          }
                          className="mt-1 mr-3"
                        />
                        <Label
                          htmlFor="claimType1"
                          className="text-foreground cursor-pointer"
                        >
                          <span className="font-medium">
                            Disability Compensation
                          </span>
                          <span className="block text-sm text-muted-foreground">
                            For conditions related to military service
                          </span>
                        </Label>
                      </div>

                      <div className="flex items-start">
                        <Checkbox
                          id="claimType2"
                          checked={formData.claimTypes.includes("appeal")}
                          onCheckedChange={() => handleCheckboxChange("appeal")}
                          className="mt-1 mr-3"
                        />
                        <Label
                          htmlFor="claimType2"
                          className="text-foreground cursor-pointer"
                        >
                          <span className="font-medium">
                            Appeal Existing Claim
                          </span>
                          <span className="block text-sm text-muted-foreground">
                            For denied or underrated claims
                          </span>
                        </Label>
                      </div>

                      <div className="flex items-start">
                        <Checkbox
                          id="claimType3"
                          checked={formData.claimTypes.includes("education")}
                          onCheckedChange={() =>
                            handleCheckboxChange("education")
                          }
                          className="mt-1 mr-3"
                        />
                        <Label
                          htmlFor="claimType3"
                          className="text-foreground cursor-pointer"
                        >
                          <span className="font-medium">
                            Education Benefits
                          </span>
                          <span className="block text-sm text-muted-foreground">
                            GI Bill and education assistance
                          </span>
                        </Label>
                      </div>

                      <div className="flex items-start">
                        <Checkbox
                          id="claimType4"
                          checked={formData.claimTypes.includes("home")}
                          onCheckedChange={() => handleCheckboxChange("home")}
                          className="mt-1 mr-3"
                        />
                        <Label
                          htmlFor="claimType4"
                          className="text-foreground cursor-pointer"
                        >
                          <span className="font-medium">
                            Home Loan Benefits
                          </span>
                          <span className="block text-sm text-muted-foreground">
                            VA home loan assistance
                          </span>
                        </Label>
                      </div>

                      <div className="flex items-start">
                        <Checkbox
                          id="claimType5"
                          checked={formData.claimTypes.includes("discharge")}
                          onCheckedChange={() =>
                            handleCheckboxChange("discharge")
                          }
                          className="mt-1 mr-3"
                        />
                        <Label
                          htmlFor="claimType5"
                          className="text-foreground cursor-pointer"
                        >
                          <span className="font-medium">
                            Discharge Upgrade
                          </span>
                          <span className="block text-sm text-muted-foreground">
                            Changing discharge characterization
                          </span>
                        </Label>
                      </div>

                      <div className="flex items-start">
                        <Checkbox
                          id="claimType6"
                          checked={formData.claimTypes.includes("other")}
                          onCheckedChange={() => handleCheckboxChange("other")}
                          className="mt-1 mr-3"
                        />
                        <Label
                          htmlFor="claimType6"
                          className="text-foreground cursor-pointer"
                        >
                          <span className="font-medium">Other Benefits</span>
                          <span className="block text-sm text-muted-foreground">
                            Healthcare, pension, etc.
                          </span>
                        </Label>
                      </div>
                    </div>
                  </div>

                  <div>
                    <Label
                      htmlFor="claimDescription"
                      className="block text-muted-foreground mb-1"
                    >
                      Please briefly describe your claim or what you're seeking
                      assistance with:
                    </Label>
                    <Textarea
                      id="claimDescription"
                      value={formData.claimDescription}
                      onChange={(e) =>
                        updateFormData("claimDescription", e.target.value)
                      }
                      placeholder="e.g., 'I have ringing in my ears from my time on the flight line...' or 'I need to appeal a denied claim for my knee.'"
                      className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-navy"
                      rows={5}
                    />
                  </div>

                  <div>
                    <Label className="block text-muted-foreground mb-3">
                      Have you previously filed a claim with the VA?
                    </Label>
                    <RadioGroup
                      value={formData.previousClaim}
                      onValueChange={(value) =>
                        updateFormData("previousClaim", value)
                      }
                      className="flex items-center space-x-6"
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="yes" id="prevClaimYes" />
                        <Label htmlFor="prevClaimYes">Yes</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="no" id="prevClaimNo" />
                        <Label htmlFor="prevClaimNo">No</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="unsure" id="prevClaimUnsure" />
                        <Label htmlFor="prevClaimUnsure">I'm not sure</Label>
                      </div>
                    </RadioGroup>
                  </div>
                </div>

                <div className="pt-4 flex justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    className="px-6 py-3 border border-navy text-navy rounded-md hover:bg-neutral-200 transition-colors"
                    onClick={prevStep}
                  >
                    <i className="fas fa-arrow-left mr-2"></i> Back
                  </Button>

                  <Button
                    type="button"
                    className="px-6 py-3 gold text-navy rounded-md hover:bg-gold-light transition-colors font-bold"
                    onClick={submitForm}
                  >
                    <i className="fas fa-paper-plane mr-2"></i> Submit Claim
                    Information
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

