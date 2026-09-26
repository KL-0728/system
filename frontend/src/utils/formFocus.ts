import type { FormEvent } from 'react';

/** Close the mobile keyboard before an async submit changes the page layout. */
export function releaseFormFocus(event: FormEvent<HTMLFormElement>) {
  const focused = document.activeElement;
  if (focused instanceof HTMLElement && event.currentTarget.contains(focused)) focused.blur();
}
