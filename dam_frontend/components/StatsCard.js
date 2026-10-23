import { Box, Heading, Text, HStack } from "@chakra-ui/react";

export default function StatsCard({ title, value, subtitle }){
  return (
    <Box p={5} bg="white" borderRadius="lg" boxShadow="md">
      <Heading size="md">{title}</Heading>
      <HStack mt={3} justify="space-between">
        <Text fontSize="2xl" fontWeight="bold">{value}</Text>
        <Text fontSize="sm" color="gray.500">{subtitle}</Text>
      </HStack>
    </Box>
  );
}
