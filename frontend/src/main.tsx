import React from 'react'
import ReactDOM from 'react-dom/client'
import { Amplify } from 'aws-amplify'
import { AwsRum } from 'aws-rum-web'
import amplifyConfig from './amplify-config'
import App from './App.tsx'
import './index.css'

Amplify.configure(amplifyConfig)

// CloudWatch RUM — captures JS errors, HTTP failures, page views in production
try {
  new AwsRum(
    "1765006c-f06d-4a71-bd10-3c98c3d1ba06",
    "1.0.0",
    "us-east-1",
    {
      sessionSampleRate: 1,
      identityPoolId: "us-east-1:e787e729-fced-4892-8d7b-a5fe72f53cbd",
      guestRoleArn: "arn:aws:iam::973028704465:role/ValorAssist-RUM-GuestRole",
      endpoint: "https://dataplane.rum.us-east-1.amazonaws.com",
      telemetries: ["errors", "http", "performance"],
      allowCookies: true,
      enableXRay: false,
    }
  );
} catch {
  // RUM init failure must never break the app
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
