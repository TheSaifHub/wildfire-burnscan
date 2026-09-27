"use client";

import dynamic from "next/dynamic";

const FireMap = dynamic(() => import("./FireMap"), {
  ssr: false,
  loading: () => (
    <div className="h-[500px] w-full rounded-lg border flex items-center justify-center text-gray-400">
      Loading map...
    </div>
  ),
});

export default function MapLoader(props) {
  return <FireMap {...props} />;
}
