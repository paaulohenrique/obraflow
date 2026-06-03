import { cn } from "@/lib/utils"

export function Table({ className, children, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative overflow-x-auto">
      <table className={cn("w-full min-w-max border-separate border-spacing-0 text-sm", className)} {...props}>
        {children}
      </table>
    </div>
  )
}

export function Thead({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn("sticky top-0 z-10 border-b border-zinc-200 bg-zinc-50/95 backdrop-blur", className)} {...props}>
      {children}
    </thead>
  )
}

export function Th({ className, children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "h-10 border-b border-zinc-200 px-4 text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-500 whitespace-nowrap",
        className
      )}
      {...props}
    >
      {children}
    </th>
  )
}

export function Tbody({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody
      className={cn("bg-white", className)}
      {...props}
    >
      {children}
    </tbody>
  )
}

export function Tr({
  className,
  clickable,
  children,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement> & { clickable?: boolean }) {
  return (
    <tr
      className={cn(
        "group transition-colors duration-150",
        clickable && "cursor-pointer hover:bg-orange-50/35",
        className
      )}
      {...props}
    >
      {children}
    </tr>
  )
}

export function Td({ className, children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("border-b border-zinc-100 px-4 py-3 text-zinc-700 whitespace-nowrap", className)} {...props}>
      {children}
    </td>
  )
}
