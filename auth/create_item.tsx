import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Item } from "./ItemsTable";

interface CreateItemDialogProps {
  open: boolean;
  onClose: () => void;
  onCreateItem: (item: Omit<Item, "id">) => void;
}

export const CreateItemDialog = ({ open, onClose, onCreateItem }: CreateItemDialogProps) => {
  const [formData, setFormData] = useState({
    name: "",
    status: "todo" as Item["status"],
    priority: "medium" as Item["priority"],
    assignee: "",
    dueDate: "",
    progress: 0,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    
    onCreateItem(formData);
    setFormData({
      name: "",
      status: "todo",
      priority: "medium",
      assignee: "",
      dueDate: "",
      progress: 0,
    });
  };

  const handleChange = (field: string, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px] bg-gradient-card border-border">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-foreground">
            Criar Novo Item
          </DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-foreground">Nome da Tarefa</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="Digite o nome da tarefa"
              className="bg-input border-border text-foreground"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-foreground">Status</Label>
              <Select value={formData.status} onValueChange={(value) => handleChange("status", value)}>
                <SelectTrigger className="bg-input border-border text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border">
                  <SelectItem value="todo">To Do</SelectItem>
                  <SelectItem value="working">Working</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                  <SelectItem value="stuck">Stuck</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-foreground">Prioridade</Label>
              <Select value={formData.priority} onValueChange={(value) => handleChange("priority", value)}>
                <SelectTrigger className="bg-input border-border text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border">
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="assignee" className="text-foreground">Responsável</Label>
            <Input
              id="assignee"
              value={formData.assignee}
              onChange={(e) => handleChange("assignee", e.target.value)}
              placeholder="Nome do responsável"
              className="bg-input border-border text-foreground"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="dueDate" className="text-foreground">Data de Entrega</Label>
            <Input
              id="dueDate"
              type="date"
              value={formData.dueDate}
              onChange={(e) => handleChange("dueDate", e.target.value)}
              className="bg-input border-border text-foreground"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="progress" className="text-foreground">Progresso (%)</Label>
            <Input
              id="progress"
              type="number"
              min="0"
              max="100"
              value={formData.progress}
              onChange={(e) => handleChange("progress", parseInt(e.target.value) || 0)}
              className="bg-input border-border text-foreground"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="border-border text-foreground hover:bg-muted"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              className="bg-gradient-primary hover:shadow-glow transition-all duration-300"
            >
              Criar Item
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};