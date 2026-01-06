import { NextRequest, NextResponse } from "next/server";

const LEETCODE_API_BASE = "https://leetcode-api-pied.vercel.app";

export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url);
        const endpoint = searchParams.get("endpoint");

        if (!endpoint) {
            return NextResponse.json(
                { error: "Missing endpoint parameter" },
                { status: 400 }
            );
        }

        // Make request to the external LeetCode API
        const response = await fetch(`${LEETCODE_API_BASE}${endpoint}`, {
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (!response.ok) {
            return NextResponse.json(
                { error: `LeetCode API error: ${response.status}` },
                { status: response.status }
            );
        }

        const data = await response.json();

        // Return the data with CORS headers
        return NextResponse.json(data, {
            headers: {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        });
    } catch (error) {
        console.error("Error proxying LeetCode API:", error);
        return NextResponse.json(
            { error: "Failed to fetch data from LeetCode API" },
            { status: 500 }
        );
    }
}

export async function OPTIONS() {
    return new NextResponse(null, {
        status: 200,
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    });
}
