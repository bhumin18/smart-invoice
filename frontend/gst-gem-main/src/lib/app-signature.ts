const developerCodepoints = [
  66, 104, 117, 109, 105, 110, 32, 80, 97, 108, 97, 100, 105, 121, 97,
] as const;

const profileUrlCodepoints = [
  104, 116, 116, 112, 115, 58, 47, 47, 119, 119, 119, 46, 108, 105, 110, 107, 101, 100, 105, 110,
  46, 99, 111, 109, 47, 105, 110, 47, 98, 104, 117, 109, 105, 110, 45, 112, 97, 108, 97, 100, 105,
  121, 97,
] as const;

export const APP_NAME = "GST Invoice Pro";
export const DEVELOPER_NAME = String.fromCharCode(...developerCodepoints);
export const DEVELOPER_SIGNATURE = `Developed by ${DEVELOPER_NAME}`;
export const DEVELOPER_PROFILE_URL = String.fromCharCode(...profileUrlCodepoints);

export type AppBranding = {
  appName: string;
  developerName: string;
  developerSignature: string;
  developerProfileUrl: string;
};

export const FALLBACK_BRANDING: AppBranding = {
  appName: APP_NAME,
  developerName: DEVELOPER_NAME,
  developerSignature: DEVELOPER_SIGNATURE,
  developerProfileUrl: DEVELOPER_PROFILE_URL,
};
