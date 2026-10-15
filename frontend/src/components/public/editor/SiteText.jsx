import { useId } from "react";
import { useSite } from "../../../lib/site";
import { getPath } from "./editorFields";

export const UI_TEXT = {
  menu: "Menu", privacy: "Privacy", skip: "Skip to content", home: "Home", our_work: "Our Work",
  field_notes: "Field Notes", search_notes: "Search Field Notes", search: "Search", all_topics: "All topics",
  note_singular: "note", note_plural: "notes", matching: "matching", in_category: "in", page: "Page",
  empty_notes: "No Field Notes have been published here yet.", related_notes: "Related Field Notes",
  note_by: "By", note_published: "Published", note_updated: "Updated", credits: "Credits",
  references: "References", source: "source", downloads: "Downloads", download: "Download",
  kind_article: "Article", kind_photo_essay: "Photo essay", kind_interview: "Interview", kind_workshop_reflection: "Workshop reflection", kind_resource: "Resource",
  contact_name: "Name", contact_email: "Email", contact_topic: "Enquiry topic", choose_topic: "Choose a topic",
  contact_message: "Message", contact_phone: "Phone", contact_organisation: "Organisation", optional: "optional",
  topic_general: "General", topic_collaboration: "Collaboration", topic_volunteer: "Volunteer", topic_craft: "Craft", topic_theatre: "Theatre", topic_workshops: "Workshops & Learning",
  send_message: "Send message", sending: "Sending…", contact_thanks: "Thank you — your message has been received.",
  contact_stored: "It is stored securely for the USP India team. Email notifications are not yet switched on, so replies may take a little longer.", contact_notified: "The team has been notified.",
  error_name: "Please enter your name.", error_email: "Please enter a valid email address.", error_topic: "Please choose a topic.", error_message: "Please write a message of at least 10 characters.", error_phone: "Phone may contain digits, spaces and + ( ) - only.",
  not_found: "Page not found", not_found_body: "This address does not exist on the USP India website.", go_home: "Go to Home", read_notes: "Read Field Notes",
  film_pending: "Film link pending", four_areas: "Four areas of work", watch_video: "Watch the video", transcript: "Transcript",
};
export const textFor = (site, key) => site?.ui_text?.[key] ?? UI_TEXT[key] ?? key;
export function SiteText({ path, name, fallback, as: Tag = "span", children, ...props }) {
  const site = useSite();
  const id = useId().replace(/:/g, "");
  const field = path || `ui_text.${name}`;
  const value = getPath(site, field) ?? fallback ?? children ?? UI_TEXT[name] ?? "";
  return <Tag {...props} data-site-edit={field} data-testid={props["data-testid"] || `site-text-${field.replace(/\./g, "-")}-${id}`}>{value}</Tag>;
}