export function Logo({ size = 18 }: { size?: number }) {
  return (
    <span style={{ fontSize: size }} className="font-extrabold">
      <span className="font-serif font-bold">言の葉</span>
      <span className="ml-2 font-ui text-[0.8em] font-semibold opacity-70">Kotonoha</span>
    </span>
  );
}
