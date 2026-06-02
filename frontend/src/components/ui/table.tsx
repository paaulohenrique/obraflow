import { cn } from "@/lib/utils"

export function Table({ className, children, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full text-sm", className)} {...props}>
        {children}
      </table>
    </div>
  )
}

export function Thead({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn("bg-zinc-50 border-b border-zinc-200", className)} {...props}>
      {children}
    </thead>
  )
}

export function Th({ className, children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "h-10 px-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wide whitespace-nowrap",
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
      className={cn("divide-y divide-zinc-100 bg-white", className)}
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
        "transition-colors duration-100",
        clickable && "cursor-pointer hover:bg-zinc-50/80",
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
    <td className={cn("px-4 py-3 text-zinc-700 whitespace-nowrap", className)} {...props}>
      {children}
    </td>
  )
}
