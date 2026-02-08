// ============================================================================
// TeamCombobox — searchable team picker using shadcn Command
// ============================================================================

import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { ChevronsUpDown, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Team } from '@/lib/types'

interface TeamComboboxProps {
  teams: Team[]
  value: string
  onSelect: (teamId: string) => void
  placeholder?: string
}

export function TeamCombobox({
  teams,
  value,
  onSelect,
  placeholder = 'Select team…',
}: TeamComboboxProps) {
  const [open, setOpen] = useState(false)

  const selectedLabel = useMemo(
    () => teams.find((t) => t.id === value)?.meta.school ?? '',
    [teams, value],
  )

  return (
    <>
      <Button
        variant="outline"
        role="combobox"
        aria-expanded={open}
        className="w-full justify-between font-normal"
        onClick={() => setOpen(true)}
      >
        {selectedLabel || <span className="text-muted-foreground">{placeholder}</span>}
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="p-0 gap-0 max-w-md">
          <DialogTitle className="sr-only">Select a team</DialogTitle>
          <Command
            filter={(value, search) => {
              const q = search.toLowerCase()
              return value.toLowerCase().includes(q) ? 1 : 0
            }}
          >
            <CommandInput placeholder="Search teams…" />
            <CommandList>
              <CommandEmpty>No teams found.</CommandEmpty>
              <CommandGroup>
                {teams.map((team) => (
                  <CommandItem
                    key={team.id}
                    value={`${team.meta.school} ${team.meta.name} ${team.id} ${team.meta.ncaa_key ?? ''} ${team.meta.location}`}
                    onSelect={() => {
                      onSelect(team.id)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        value === team.id ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                    <span className="font-medium">{team.meta.school}</span>
                    <span className="ml-2 text-muted-foreground text-sm">
                      {team.meta.location}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </DialogContent>
      </Dialog>
    </>
  )
}
