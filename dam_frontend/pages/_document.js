import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="en">
      <Head />
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const username = localStorage.getItem("username");
                const role = localStorage.getItem("role");
                if (!username || !role) {
                  localStorage.setItem("username", "Guest");
                  localStorage.setItem("role", "User");
                }
              } catch (e) {}
            `,
          }}
        />
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
