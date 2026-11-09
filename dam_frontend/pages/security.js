import { Box, Heading, Text, Link, VStack } from "@chakra-ui/react";

export default function SecurityGuidance() {
  return <Box maxW="720px" mx="auto" p={8}>
    <Heading mb={6}>Security and privacy</Heading>
    <VStack align="stretch" spacing={4}>
      <Text>Check the site address and HTTPS connection before signing in. Stop if your browser reports a certificate warning and contact your administrator.</Text>
      <Text>Use a unique, strong password. Never share your password, access tokens, or browser session. Log out when finished, especially on shared devices.</Text>
      <Text>Upload only files you are authorized to store. Avoid personal or confidential information unless your organization has approved its use here. Check asset permissions before sharing.</Text>
      <Text>Security events may record your account, network address, action, and time for investigation. Ask your administrator about access, retention, and deletion requests.</Text>
      <Text>Report unexpected access, suspicious files, or account activity to your project administrator. Include the time and action; do not send passwords or tokens.</Text>
      <Link href="/login" color="purple.600">Return to sign in</Link>
    </VStack>
  </Box>;
}
